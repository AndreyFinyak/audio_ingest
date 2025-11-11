from fastapi import APIRouter

from app.api.audio import router as audio_router

main_router = APIRouter()

main_router.include_router(audio_router)
