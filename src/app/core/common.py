import logging

from app.core.config import settings


def configure_logging(level: str) -> None:
    """Конфигурация логирования для всего приложения."""
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format=(
            "[%(asctime)s.%(msecs)03d] %(module)-20s:%(lineno)3d "
            "%(levelname)-7s - %(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )
