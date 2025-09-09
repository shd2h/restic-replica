import logging
from pathlib import Path
import platform
import shutil
from subprocess import CalledProcessError, CompletedProcess
import tomllib
from typing import Optional

from restic_replica.repository import Repository, ResticCli

logger = logging.getLogger(__name__)


# TODO: write into AppData for windows.
def ensure_config_file(config_file: Optional[Path] = None) -> Path:
    """
    Search for config file in expected location. If one does not exist, create one, then raise SystemExit.

    Args:
        config_file: path to the application configuration file, which may or may not exist.

    Returns:
        config_file: path to the application configuration file, which is confirmed to exist.

    Raises:
        SystemExit: if no configuration file exists, this exception is raised after an example configuration file has been created.
    """
    # set default path if one was not supplied
    if not config_file:
        config_file = Path.home() / ".restic-replica" / "config.toml"
    # create config file and parent dir if config file does not exist
    if not config_file.exists():
        print("ERROR: Missing configuration file")
        config_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            Path("src/restic_replica/__assets__/example_config.toml"), config_file
        )
        print(
            f"An example configuration file has been created at {config_file}. Update the configuration in this file to match your system, and then re-run this program."
        )
        raise SystemExit(0)
    else:
        return config_file


def read_config_file(config_file: Path) -> dict:
    try:
        with open(config_file, "rb") as f:
            return tomllib.load(f)
    except Exception as err:
        print(f"ERROR: {err}")
        raise


def get_restic(config: dict) -> ResticCli:
    """return a ResticCli instance populated with the information from config"""
    # if the restic path is not specified, set it
    try:
        path = Path(config["path"])
    except KeyError:
        if platform.system() == "Windows":
            path = Path("restic.exe")
        else:
            path = Path("restic")
    # environment variables
    try:
        env = config["environment"]
    except KeyError:
        env = {}
    # set RESTIC_PROGRESS_FPS if it isn't set
    if "RESTIC_PROGRESS_FPS" not in env.keys():
        env["RESTIC_PROGRESS_FPS"] = "0.016667"  # update every minute
    return ResticCli(path, environment_vars=env)


def get_repository(name: str, config: dict, restic_cli: ResticCli) -> Repository:
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
        restic_cli,
        password=password,
        password_file=password_file,
        password_command=password_command,
        environment_vars=env,
    )


def check_repository_access(repository: Repository) -> bool:
    try:
        return bool(repository.snapshots())
    except CalledProcessError as err:
        logger.error(err)
        raise RuntimeError(f"Unable to access restic repository {repository}") from err


def copy_snapshots(
    source_repository: Repository, destination_repository: Repository
) -> CompletedProcess:
    try:
        return destination_repository.copy(source_repository, live_output=True)
    except CalledProcessError as err:
        logger.error(err)
        raise RuntimeError(
            f"error copying snapshots from {source_repository.uri} to {destination_repository.uri}"
        ) from err
