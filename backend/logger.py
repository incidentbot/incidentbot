import logging
import os
import sys

from pythonjsonlogger import jsonlogger

log_level = os.getenv("LOGLEVEL", "INFO").upper()

logger = logging.getLogger()
logHandler = logging.StreamHandler(stream=sys.stdout)
formatter = jsonlogger.JsonFormatter(
    "%(name)s %(asctime)s %(levelname)s %(filename)s %(message)s"
)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(log_level)
