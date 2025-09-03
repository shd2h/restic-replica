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
        logger.error(err)
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
        password_file = config["password_file"]
    except KeyError:
        password_file = None
    try:
        password_command = config["password_command"]
    except KeyError:
        password_command = None
    try:
        env = config["environment"]
    except KeyError:
        env = None
    return Repository(
        uri,
        name,
        password=password,
        password_file=password_file,
        password_command=password_command,
        environment_vars=env,
    )


def check_repository_access(repository: Repository) -> None:
    try:
        repository.snapshots()
    except CalledProcessError as err:
        logger.error(err)
        raise RuntimeError(f"Unable to access restic repository {repository}") from err


def copy_snapshots(source_repository: Repository, target_repository: Repository):
    try:
        target_repository.copy(source_repository)
    except CalledProcessError as err:
        logger.error(err)
        raise RuntimeError(
            "error copying snapshots from {source_repository} to {target_repository}"
        ) from err
