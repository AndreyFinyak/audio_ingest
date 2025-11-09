import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    func,
    TIMESTAMP,
    String,
    Integer,
    Enum as EnumORM,
    ForeignKey,
    Float,
    JSON,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class StatusUploadEnum(Enum):
    receiving = "receiving"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class JobStatusEnum(Enum):
    "queued", "in_progress", "done", "failed"
    queued = "queued"
    in_progress = "in_progress"
    done = "done"
    failed = "failed"


class Base(DeclarativeBase):
    pass


# ----------------------------------------------------------------------
# Таблица uploads — хранит информацию о процессе загрузки
# ----------------------------------------------------------------------
class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[StatusUploadEnum] = mapped_column(
        EnumORM,
        default="receiving",
        nullable=False,
    )
    uploaded_bytes: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=func.now)
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now,
        onupdate=func.now
    )

    jobs: Mapped[list["Job"]] = relationship(
        back_populates="upload", cascade="all, delete-orphan"
    )
    audio_files: Mapped[list["AudioFile"]] = relationship(
        back_populates="upload", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return (
            f"Upload(id={self.id}, filename={self.filename},"
            f"content_type={self.content_type}, size_bytes={self.size_bytes})"
        )


# ----------------------------------------------------------------------
# Таблица jobs — очередь фоновых задач
# ----------------------------------------------------------------------
class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    upload_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("uploads.id", ondelete="CASCADE"),
        nullable=False
    )
    type: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    status: Mapped[JobStatusEnum] = mapped_column(
        EnumORM,
        nullable=False,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[dict | None] = mapped_column(JSON)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=func.now)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=func.now,
        onupdate=func.now
    )

    upload: Mapped["Upload"] = relationship(back_populates="jobs")

    __table_args__ = (
        UniqueConstraint("upload_id", "type", name="uq_jobs_upload_type"),
    )

    def __repr__(self):
        return (
            f"Job(id={self.id}, upload_id={self.upload_id},"
            f"type={self.type}, status={self.status})"
        )


# ----------------------------------------------------------------------
# Таблица audio_files — итоговые файлы после обработки
# ----------------------------------------------------------------------
class AudioFile(Base):
    __tablename__ = "audio_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    upload_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("uploads.id", ondelete="CASCADE"),
        nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    duration_s: Mapped[float] = mapped_column(Float)
    channels: Mapped[int] = mapped_column(Integer)
    sample_rate: Mapped[int] = mapped_column(Integer)
    format: Mapped[str] = mapped_column(String(32))
    rms_avg: Mapped[float | None] = mapped_column(Float)
    zcr_avg: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(default=func.now)

    upload: Mapped["Upload"] = relationship(back_populates="audio_files")
    segments: Mapped[list["Segment"]] = relationship(
        back_populates="audio_file", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return (
            f"AudioFile(id={self.id}, upload_id={self.upload_id},"
            f"file_path={self.file_path})"
        )


# ----------------------------------------------------------------------
# Таблица segments — куски речи внутри файла
# ----------------------------------------------------------------------
class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    audio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audio_files.id", ondelete="CASCADE"),
        nullable=False
    )
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    rms: Mapped[float | None] = mapped_column(Float)
    zcr: Mapped[float | None] = mapped_column(Float)
    transcript: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    audio_file: Mapped["AudioFile"] = relationship(back_populates="segments")

    def __repr__(self):
        return (
            f"Segment(id={self.id}, audio_id={self.audio_id},"
            f"start_ms={self.start_ms}, end_ms={self.end_ms})"
        )
