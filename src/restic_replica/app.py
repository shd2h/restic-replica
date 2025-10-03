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
from restic_replica.snapshots import Policy, SnapshotList

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


def get_policy(config: dict) -> Optional[Policy]:
    """
    Return a Policy instance populated with the information from config

    Args:
        config: policy configuration dictionary

    Returns:
        a populated Policy instance

    Raises:
        RuntimeError: raised if the policy is invalid, or invalid policy options are read from the config.
    """
    user_set_policy = False
    try:
        keep_last = config["keep-last"]
        user_set_policy = True
    except KeyError:
        keep_last = 0
    try:
        keep_daily = config["keep-daily"]
        user_set_policy = True
    except KeyError:
        keep_daily = 0
    try:
        keep_weekly = config["keep-weekly"]
        user_set_policy = True
    except KeyError:
        keep_weekly = 0
    try:
        keep_monthly = config["keep-monthly"]
        user_set_policy = True
    except KeyError:
        keep_monthly = 0
    try:
        keep_yearly = config["keep-yearly"]
        user_set_policy = True
    except KeyError:
        keep_yearly = 0
    try:
        no_current = config["exclude-current-period"]
    except KeyError:
        no_current = False

    # if user set any values, return a policy, else return none
    if user_set_policy:
        try:
            return Policy(
                keep_last,
                keep_daily,
                keep_weekly,
                keep_monthly,
                keep_yearly,
                no_current,
            )
        except (ValueError, TypeError) as err:
            raise RuntimeError(
                "Invalid policy; all keep-* options set in the config file must be non-negative integers, and at least one must be non-zero."
            ) from err
    else:
        return None


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

    Args:
        repository: the Repository instance to check access for

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


def get_filtered_snapshots(repository: Repository, policy: Policy) -> SnapshotList:
    """"""
    snaps = SnapshotList.from_json(repository.snapshots(json=True).stdout)
    filtered_snaps = SnapshotList(snaps.filter(policy))
    if len(filtered_snaps.snapshots) > 0:
        return filtered_snaps
    else:
        raise RuntimeError("snapshot filtering led to 0 snapshots to copy")


def copy_snapshots(
    source_repository: Repository,
    destination_repository: Repository,
    policy: Optional[Policy] = None,
    dry_run: bool = False,
) -> CompletedProcess:
    """
    Copy snapshots from source_repository repository to destination_repository

    Args:
        source_repository: the Repository instance snapshots will be copied _from_
        destination_repository: the Repository instance snapshots will be copied _to_
        policy: an optional Policy instance that will be applied to filter the list of snapshots that will be copied
        dry_run: whether to actually perform the copy operation or not

    Returns:
        a populated CompletedProcess instance

    Raises:
        RunTimeError: raised if operation fails
        SystemExit: raised instead of performing the copy process, if dry_run is set
    """
    try:
        if policy:
            logger.info(
                f"Filtering snapshots to be copied from source repository using policy: {policy}"
            )
            filtered_snapshots = get_filtered_snapshots(source_repository, policy)
            logger.info(f"The following snapshots will be copied: {filtered_snapshots}")
        else:
            logger.info(
                "No policy specified, all snapshots will be copied from the source repository"
            )
            filtered_snapshots = None
        if dry_run:
            logger.info("dry-run flag set, exiting without performing copy operation")
            raise SystemExit(0)
        else:
            logger.info(
                f"Starting copy of snapshots from {source_repository.uri} to {destination_repository.uri}"
            )
            return destination_repository.copy(
                source_repository,
                live_output=True,
                snapshots=filtered_snapshots,
            )
    except (CalledProcessError, OSError) as err:
        logger.error(err)
        raise RuntimeError(
            f"error copying snapshots from {source_repository.uri} to {destination_repository.uri}"
        ) from err
