import logging.config
from pathlib import Path

LOGGING_CONF_PATH = Path(__file__).with_name('logging.conf')

logging.config.fileConfig(LOGGING_CONF_PATH)
logging.getLogger(__name__).info('Logging is configured.')
