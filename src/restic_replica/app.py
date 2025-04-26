from configparser import ConfigParser
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def read_config_file(config_file: Path) -> ConfigParser:
    config = ConfigParser()
    if not config_file:
        config_file = Path.cwd().joinpath("config_file")
        return config
    try:
        config.read(config_file)
    except Exception as err:
        print(f"ERROR: {err}")
        raise


def logging_headers(version: str) -> None:
    logging.info("==============================")
    logging.info(f"  restic-replica {version}")
    logging.info("==============================")


def check_repository_access():
    pass
