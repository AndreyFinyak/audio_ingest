from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.core.containers import Container
from app.schemas import AudioFileRead, UploadRead
from app.services.audio_service import AudioService

router = APIRouter(prefix="/audio", tags=["audio"])


@router.get("/uploads", response_model=list[UploadRead])
@inject
async def get_uploads(
    audio_service: AudioService = Depends(Provide[Container.audio_service]),
):
    return await audio_service.get_uploads()


@router.get("/{upload_id}", response_model=AudioFileRead)
@inject
async def get_audio_info(
    audio_service: AudioService = Depends(Provide[Container.audio_service]),
    upload_id: int = Query(..., ge=1),
):
    audio = await audio_service.get_audio_info(upload_id)
    if not audio:
        raise HTTPException(status_code=404, detail="Audio not found")
    return audio


@router.get("/{upload_id}/download", response_model=FileResponse)
@inject
async def download_audio(
    audio_service: AudioService = Depends(Provide[Container.audio_service]),
    upload_id: int = Query(..., ge=1),
):
    file_path = await audio_service.get_upload_file_path(upload_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        file_path, media_type="audio/wav", filename=f"{upload_id}.wav"
    )
