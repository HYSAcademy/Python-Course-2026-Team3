import sys
from loguru import logger
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

COLOR_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<magenta>[{extra[correlation_id]}]</magenta> - "
    "<level>{message}</level>"
)


PLAIN_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss} | "
    "{level: <8} | "
    "{name}:{function}:{line} - "
    "[{extra[correlation_id]}] - "
    "{message}"
)

logger.configure(extra={"correlation_id": "SYSTEM"})

logger.remove()


logger.add(sys.stderr, format=COLOR_FORMAT, level="INFO", colorize=True, enqueue=True)


logger.add(
    LOG_DIR / "app.log",
    format=PLAIN_FORMAT,
    level="INFO",
    colorize=False,
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    enqueue=True,
    backtrace=False,
    diagnose=False,
)


logger.add(
    LOG_DIR / "errors.log",
    format=PLAIN_FORMAT,
    level="ERROR",
    colorize=False,
    rotation="15 MB",
    retention="60 days",
    compression="zip",
    enqueue=True,
    backtrace=True,
    diagnose=True,
)

__all__ = ["logger"]
