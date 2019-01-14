import logging.config
from pathlib import Path

FILE_VERSION: int = 1
FILENAME_ENCODING: str = 'urlsafe_b64'  # Options: urlsafe_b64, b32, b16
NUM_RANDOM_BITS: int = 256


def configure_logging() -> None:
    path = Path(__file__).with_name('logging.conf')
    logging.config.fileConfig(path)
    log = logging.getLogger(__name__)
    log.info('Logging is configured.')
