from dependency_injector import containers, providers

from app.services.audio_service import AudioService


class Container(containers.DeclarativeContainer):
    """
    Контейнер зависимостей приложения.
    """

    audio_service = providers.Singleton(AudioService)
