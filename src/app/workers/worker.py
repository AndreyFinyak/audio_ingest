import asyncio
import aiofiles
import io
import logging
import wave

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Job,
    Upload,
    AudioFile,
    Segment,
    StatusUploadEnum,
    JobStatusEnum,
)
from app.db.database import connection
from app.core.config import worker_settings

logger = logging.getLogger(__name__)


MAX_ATTEMPTS = worker_settings.MAX_ATTEMPTS
RETRY_BASE_DELAY = worker_settings.RETRY_BASE_DELAY


class Worker:
    def __init__(self, stop_event: asyncio.Event):
        self.stop_event = stop_event

    async def worker_loop(self) -> None:
        """
        Главный цикл фонового воркера.
        Запускается при старте FastAPI (через on_startup).
        """
        logger.info("Worker started")
        while not self.stop_event.is_set():
            job = await self._fetch_next_job()
            if not job:
                await asyncio.sleep(2)
                continue
            try:
                await self._process_job(job)
            except Exception as e:
                logger.exception("Job %s failed: %s", job.id, e)
                await self._handle_failure(job, str(e))
            await asyncio.sleep(0)
        logger.info("Worker stopped")

    @connection
    async def _fetch_next_job(self, session: AsyncSession) -> Job | None:
        """Берём одну задачу analyze со статусом queued (с блокировкой)."""
        q = (
            select(Job)
            .where(Job.type == "analyze", Job.status == JobStatusEnum.queued)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        res = await session.execute(q)
        job = res.scalar_one_or_none()
        if not job:
            return None

        job.status = JobStatusEnum.in_progress
        job.attempts += 1
        await session.commit()
        logger.info("Picked job %s", job.id)
        return job

    @connection
    async def _process_job(self, job: Job, session: AsyncSession) -> None:
        """Основная логика анализа аудио."""
        upload = await session.get(Upload, job.upload_id)
        if not upload:
            raise RuntimeError("Upload not found")

        file_path = f"storage/uploads/{upload.id}/file"
        logger.info("Processing file %s", file_path)

        # читаем файл
        async with aiofiles.open(file_path, "rb") as f:
            wav_bytes = await f.read()

        loop = asyncio.get_running_loop()
        meta, segments = await loop.run_in_executor(
            None,
            analyze_audio_bytes,
            wav_bytes
        )

        # создаём AudioFile
        audio = AudioFile(
            upload_id=upload.id,
            file_path=file_path,
            duration_s=meta["duration_s"],
            channels=meta["channels"],
            sample_rate=meta["sample_rate"],
            format=meta["format"],
            rms_avg=meta["rms_avg"],
            zcr_avg=meta["zcr_avg"],
        )
        session.add(audio)
        await session.flush()  # чтобы получить audio.id

        for seg in segments:
            session.add(
                Segment(
                    audio_id=audio.id,
                    start_ms=seg["start_ms"],
                    end_ms=seg["end_ms"],
                    rms=seg["rms"],
                    zcr=seg["zcr"],
                    transcript="(placeholder)",
                )
            )

        job.status = JobStatusEnum.done
        upload.status = StatusUploadEnum.ready
        await session.commit()
        logger.info("Job %s finished successfully", job.id)

    @connection
    async def _handle_failure(
        self,
        job: Job,
        error: str,
        session: AsyncSession
    ) -> None:
        """Обработка ошибок, экспоненциальная задержка."""
        job.last_error = error
        if job.attempts >= MAX_ATTEMPTS:
            job.status = JobStatusEnum.failed
            upload = await session.get(Upload, job.upload_id)
            if upload:
                upload.status = StatusUploadEnum.failed
            logger.error(
                "Job %s failed permanently after %s attempts",
                job.id,
                job.attempts
            )
        else:
            job.status = JobStatusEnum.queued
            delay = RETRY_BASE_DELAY * (2 ** job.attempts)
            logger.warning("Retrying job %s in %ss", job.id, delay)
            await asyncio.sleep(delay)
        await session.commit()


def analyze_audio_bytes(raw_bytes: bytes) -> tuple[dict, list[dict]]:
    """
    Выполняется в отдельном потоке через run_in_executor.
    Возвращает (метаданные, список сегментов)
    """
    with wave.open(io.BytesIO(raw_bytes), "rb") as wf:
        channels = wf.getnchannels()
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()
        duration_s = n_frames / sample_rate
        audio = np.frombuffer(wf.readframes(n_frames), dtype=np.int16)

    window_size = int(sample_rate * 0.05)  # 50мс окна
    threshold = 500
    segments = []
    rms_all, zcr_all = [], []

    in_voice = False
    seg_start = 0

    for i in range(0, len(audio), window_size):
        window = audio[i: i + window_size]
        if len(window) == 0:
            continue
        rms = float(np.sqrt(np.mean(window**2)))
        zcr = float(((window[:-1] * window[1:]) < 0).mean())
        rms_all.append(rms)
        zcr_all.append(zcr)

        if rms > threshold and not in_voice:
            in_voice = True
            seg_start = i
        elif rms <= threshold and in_voice:
            in_voice = False
            segments.append(
                dict(
                    start_ms=int(seg_start / sample_rate * 1000),
                    end_ms=int(i / sample_rate * 1000),
                    rms=rms,
                    zcr=zcr,
                )
            )

    if in_voice:
        segments.append(
            dict(
                start_ms=int(seg_start / sample_rate * 1000),
                end_ms=int(len(audio) / sample_rate * 1000),
                rms=rms_all[-1],
                zcr=zcr_all[-1],
            )
        )

    meta = dict(
        duration_s=duration_s,
        channels=channels,
        sample_rate=sample_rate,
        format="wav",
        rms_avg=float(np.mean(rms_all)),
        zcr_avg=float(np.mean(zcr_all)),
    )
    return meta, segments
