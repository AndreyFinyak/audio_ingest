from dependency_injector import containers, providers

from app.services.audio_service import AudioService
from app.workers.worker import Worker


class Container(containers.DeclarativeContainer):
    """
    Контейнер зависимостей приложения.
    """

    wiring_config = containers.WiringConfiguration(modules=["app.api.audio"])

    audio_service = providers.Singleton(AudioService)
    worker = providers.Singleton(Worker)
