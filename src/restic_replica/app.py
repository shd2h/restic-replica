import importlib.resources
import logging
from pathlib import Path
import platform
import shutil
from subprocess import CalledProcessError, CompletedProcess
import tomllib
from typing import Optional

from restic_replica import __assets__
from restic_replica.repository import Repository, ResticCli

logger = logging.getLogger(__name__)


def ensure_config_file(config_file: Optional[Path] = None) -> Path:
    """
    Search for config file in expected location. If one does not exist, create one, then raise SystemExit.

    Note: This function is called pre-logging setup, so any messages are printed to
    stdout.

    Args:
        config_file: path to the application configuration file, which may or may not exist.

    Returns:
        config_file: path to the application configuration file, which is confirmed to exist.

    Raises:
        SystemExit: if no configuration file exists, this exception is raised after an example configuration file has been created.
    """
    # set default path if one was not supplied
    if not config_file:
        if platform.system() == "Windows":
            config_file = Path.home() / "AppData/Local/restic-replica/config.toml"
        else:
            config_file = Path.home() / ".restic-replica" / "config.toml"
    # create config file and parent dir if config file does not exist
    if not config_file.exists():
        print("ERROR: Missing configuration file")
        config_file.parent.mkdir(parents=True, exist_ok=True)
        if platform.system() == "Windows":
            shutil.copyfile(
                importlib.resources.files(__assets__) / "example_config_win.toml",
                config_file,
            )
        else:
            shutil.copyfile(
                importlib.resources.files(__assets__) / "example_config.toml",
                config_file,
            )
        print(
            f"An example configuration file has been created at {config_file}. Update the configuration in this file to match your system, and then re-run this program."
        )
        raise SystemExit(0)
    else:
        return config_file


def read_config_file(config_file: Path) -> dict:
    """
    Load the toml file at config_file and return the contents as a dictionary.

    Note: This function is called pre-logging setup, so any messages are printed to
    stdout.

    Args:
        config_file: path to the application configuration file

    Returns:
        config: configuration file contents as a dictionary
    """
    try:
        with open(config_file, "rb") as f:
            return tomllib.load(f)
    except Exception as err:
        print(f"ERROR: {err}")
        raise


def get_logdir(config: dict) -> Optional[Path]:
    """
    Return the path to the logging directory specified in config, or the default log
    directory if no path is specified.

    Args:
        config: restic-replica configuration dictionary

    Returns:
        logdir: path to logging directory specified in config
    """
    try:
        return Path(config["app"]["log_directory"]).expanduser()
    except KeyError:
        if platform.system() == "Windows":
            return Path.home() / "AppData/Local/restic-replica"
        else:
            return Path.home() / ".restic-replica"


def get_restic(config: dict, verbose: Optional[int] = 0) -> ResticCli:
    """
    Return a ResticCli instance populated with the information from config

    Args:
        config: restic configuration dictionary
        verbose: verbosity level of returned ResticCli instance

    Returns:
        a populated ResticCli instance
    """
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
    return ResticCli(path, environment_vars=env, verbose=verbose)


def get_repository(name: str, config: dict, restic_cli: ResticCli) -> Repository:
    """
    Return a Repository instance populated with the information from config

    Args:
        name: friendly name for the repsository
        config: repository configuration dictionary
        restic_cli: ResticCli instance that the repository will use for operations

    Returns:
        a populated Repository instance
    """
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
    """
    Verify that a repository can be accessed successfully

    Returns:
        a boolean indicating operation success

    Raises:
        RunTimeError: raised if operation fails
    """
    try:
        return bool(repository.snapshots())
    except (CalledProcessError, OSError) as err:
        logger.error(err)
        raise RuntimeError(f"Unable to access restic repository {repository}") from err


def copy_snapshots(
    source_repository: Repository, destination_repository: Repository
) -> CompletedProcess:
    """
    Copy snapshots from source_repository repository to destination_repository

    Returns:
        a populated CompletedProcess instance

    Raises:
        RunTimeError: raised if operation fails
    """
    try:
        return destination_repository.copy(source_repository, live_output=True)
    except (CalledProcessError, OSError) as err:
        logger.error(err)
        raise RuntimeError(
            f"error copying snapshots from {source_repository.uri} to {destination_repository.uri}"
        ) from err
