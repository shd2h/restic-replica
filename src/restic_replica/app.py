from datetime import datetime
import logging
from pathlib import Path
from subprocess import CalledProcessError
import tomllib

from restic_replica.repository import Repository

logger = logging.getLogger(__name__)


def read_config_file(config_file: Path) -> dict:
    try:
        with open(config_file, "rb") as f:
            return tomllib.load(f)
    except Exception as err:
        print(f"ERROR: {err}")
        raise


def get_repository(name: str, config: dict) -> Repository:
    # non-optional config data
    uri = config["repository_uri"]
    # optional config data
    try:
        password = config["password"]
    except KeyError:
        password = None
    try:
        env = config["environment"]
    except KeyError:
        env = None
    return Repository(uri, name, password, env)


def logging_headers(version: str) -> None:
    logger.info("==============================")
    logger.info(f"  restic-replica {version}")
    logger.info("==============================")
    logger.info(f"Program start @ {datetime.now().strftime("%Y/%m/%d %H:%M:%S%z")}")


def check_repository_access(repository: Repository):
    try:
        repository.snapshots()
    except CalledProcessError as err:
        logger.error(err)
        raise RuntimeError(f"Unable to access restic repository {repository}") from err
