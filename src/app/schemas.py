from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class SegmentBase(BaseModel):
    start_ms: int
    end_ms: int
    rms: float | None = None
    zcr: float | None = None
    transcript: str | None = None


class SegmentCreate(SegmentBase):
    audio_id: UUID


class SegmentRead(SegmentBase):
    id: int
    audio_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AudioFileBase(BaseModel):
    file_path: str
    duration_s: float | None = None
    channels: int | None = None
    sample_rate: int | None = None
    format: str | None = None
    rms_avg: float | None = None
    zcr_avg: float | None = None


class AudioFileCreate(AudioFileBase):
    upload_id: UUID


class AudioFileRead(AudioFileBase):
    id: UUID
    upload_id: UUID
    created_at: datetime
    segments: list[SegmentRead] = []

    model_config = ConfigDict(from_attributes=True)


class JobBase(BaseModel):
    type: str
    status: str
    attempts: int | None = 0
    payload: dict | None = None
    last_error: str | None = None


class JobCreate(JobBase):
    upload_id: UUID


class JobRead(JobBase):
    id: UUID
    upload_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UploadBase(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    checksum_sha256: str | None = None
    status: str = "receiving"
    uploaded_bytes: int = 0
    error_message: str | None = None


class UploadCreate(UploadBase):
    pass


class UploadRead(UploadBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    jobs: list[JobRead] = []
    audio_files: list[AudioFileRead] = []

    model_config = ConfigDict(from_attributes=True)
