import os
import logging
from sqlalchemy import select

from app.db.database import connection
from app.db.models import Upload, AudioFile, Segment
from app.schemas import UploadRead, AudioFileRead

logger = logging.getLogger(__name__)


class AudioService:
    """
    Сервисный слой для работы с аудио и загрузками.
    """

    @connection
    async def get_uploads(self, session) -> list[UploadRead]:
        """
        Возвращает список всех загрузок.
        """
        q = select(Upload)
        result = await session.execute(q)
        uploads = result.scalars().all()
        logger.info("Fetched %s uploads", len(uploads))
        return [UploadRead.model_validate(u) for u in uploads]

    @connection
    async def get_audio_info(
        self,
        upload_id: str,
        session
    ) -> AudioFileRead | None:
        """
        Возвращает информацию об обработанном аудиофайле
        (AudioFile + Segments).
        """
        q_audio = select(AudioFile).where(AudioFile.upload_id == upload_id)
        result = await session.execute(q_audio)
        audio = result.scalar_one_or_none()
        if not audio:
            logger.warning("AudioFile for upload %s not found", upload_id)
            return None

        # подгружаем связанные сегменты
        q_segments = select(Segment).where(Segment.audio_id == audio.id)
        result_segments = await session.execute(q_segments)
        segments = result_segments.scalars().all()

        # подставляем сегменты для сериализации
        audio.segments = segments
        return AudioFileRead.model_validate(audio)

    @connection
    async def get_upload_file_path(
        self,
        upload_id: str,
        session
    ) -> str | None:
        """
        Возвращает путь к оригинальному файлу (для скачивания).
        """
        upload = await session.get(Upload, upload_id)
        if not upload:
            logger.warning("Upload %s not found", upload_id)
            return None

        file_path = f"storage/uploads/{upload.id}/file"
        if not os.path.exists(file_path):
            logger.error("File not found at %s", file_path)
            return None
        return file_path

    @connection
    async def get_upload_by_id(
        self,
        upload_id: str,
        session
    ) -> Upload | None:
        """
        Вспомогательный метод — получить Upload или None.
        """
        upload = await session.get(Upload, upload_id)
        return upload
