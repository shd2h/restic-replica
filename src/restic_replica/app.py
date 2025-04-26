from configparser import ConfigParser
from datetime import datetime
import logging
from pathlib import Path

from restic_replica.repository import (
    Repository,
    LocalRepository,
    SFTPRepository,
    RESTRepository,
    S3Repository,
    SwiftRepository,
    B2Repository,
    AzureRepository,
    GCSRepository,
    RcloneRepository,
)

logger = logging.getLogger(__name__)


def read_config_file(config_file: Path) -> ConfigParser:
    config = ConfigParser()
    try:
        config.read(config_file)
        return config
    except Exception as err:
        # TODO: programmatically create config file from defaults if not exist?
        print(f"ERROR: {err}")
        raise


def get_local_repository(name: str, config: dict) -> Repository:
    # TODO: no idea how to handle env vars or password passthrough as those are optional.
    return LocalRepository(uri=config["repository_uri"], name=name)


def get_sftp_repository(name: str, config: dict) -> Repository:
    return SFTPRepository(uri=config["repository_uri"], name=name)


def get_rest_repository(name: str, config: dict) -> Repository:
    return RESTRepository(uri=config["repository_uri"], name=name)


def get_s3_repository(name: str, config: dict) -> Repository:
    uri = config["repository_uri"]
    access_key_id = config["AWS_ACCESS_KEY_ID"]
    secret_access_key = config["AWS_SECRET_ACCESS_KEY"]
    session_token = config["AWS_SESSION_TOKEN"]
    return S3Repository(uri, name, access_key_id, secret_access_key, session_token)


def get_swift_repository() -> Repository:
    return SwiftRepository()


def get_b2_repository() -> Repository:
    return B2Repository()


def get_azure_repository() -> Repository:
    return AzureRepository()


def get_gcs_repository() -> Repository:
    return GCSRepository()


def get_rclone_repository() -> Repository:
    return RcloneRepository()


def get_repository(name: str, config: dict) -> Repository:
    uri = config["repository_uri"]
    uri_segments = uri.split(":")
    # local repository has no prefix
    if len(uri_segments) == 1:
        repo_type = "local"
    else:
        repo_type = uri_segments[0]

    match repo_type:
        case "local":
            return get_local_repository(name, config)
        case "sftp":
            return get_sftp_repository(name, config)
        case "rest":
            return get_rest_repository(name, config)
        case "s3":
            return get_s3_repository(name, config)
        case "swift":
            return get_swift_repository()
        case "b2":
            return get_b2_repository()
        case "azure":
            return get_azure_repository()
        case "gs":
            return get_gcs_repository()
        case "rclone":
            return get_rclone_repository()
        case _:
            raise NotImplementedError


def logging_headers(version: str) -> None:
    logging.info("==============================")
    logging.info(f"  restic-replica {version}")
    logging.info("==============================")
    logging.info(f"Program start @ {datetime.now().strftime("%Y/%m/%d %H:%M:%S%z")}")


def check_repository_access():
    pass
