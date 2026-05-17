import logging
from loguru import logger
import sys

class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

def setup_logging():
    logger.remove()
    logger.add(
        sys.stdout,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name} | {message}",
        level="DEBUG",
        colorize=True
    )
    logger.add(
        "logs/app_{time:YYYY-MM-DD}.json",
        format="{time} | {level} | {name} | {message}",
        level="INFO",
        rotation="1 day",
        retention="30 days",
        serialize=True
    )
    logging.basicConfig(handlers=[InterceptHandler()], level=0)
    return logger