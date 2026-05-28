import sys
import logging

from loguru import logger

from src.config import config

_FILE_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} — {message}"

_FILE_KWARGS = dict(
    rotation="00:00",
    retention="31 days",
    compression="gz",
    encoding="utf-8",
    enqueue=True,
    format=_FILE_FORMAT,
)


class _InterceptHandler(logging.Handler):
    """Перехватывает стандартные logging-записи и перенаправляет их в loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        # Маппим уровень stdlib → loguru
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Поднимаемся по стеку, чтобы loguru показал правильный caller
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging() -> None:
    """Настраивает loguru и перехват stdlib logging."""

    logger.remove()

    stdout_level = "DEBUG" if config.debug else "INFO"
    logger.add(
        sys.stdout,
        level=stdout_level,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
    )

    logger.add(
        "logs/{time:YYYY-MM-DD}-info.log",
        level="INFO",
        filter=lambda record: record["level"].no < logger.level("ERROR").no,
        **_FILE_KWARGS,
    )

    logger.add(
        "logs/{time:YYYY-MM-DD}-error.log",
        level="ERROR",
        **_FILE_KWARGS,
    )

    logging.basicConfig(handlers=[_InterceptHandler()], level=logging.NOTSET, force=True)

    for name in ("aiogram", "aiohttp", "asyncio"):
        logging.getLogger(name).handlers = [_InterceptHandler()]
        logging.getLogger(name).propagate = False