from dataclasses import dataclass
import logging
from pathlib import Path
import subprocess

logger = logging.getLogger(__name__)


@dataclass
class ResticCli:
    """restic binary"""

    # TODO: need to get these from the config file.
    binary: Path = Path("/usr/local/bin/restic")
    environment_vars = {"RESTIC_PROGRESS_FPS": "0.003333"}

    def execute(self, arguments: list, environment_vars={}, json=False):
        # add restic binary to args
        arguments.insert(str(self.binary), 0)
        # add json flag
        if json:
            arguments.append("--json")
        # concat env vars
        environment_vars.update(self.restic.environment_vars)
        # use Popen instead of run to get "live" output
        with subprocess.Popen(
            arguments, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        ) as process:
            for line in process.stdout:
                logging.info(line.decode("utf-8").rstrip("\n"))


@dataclass
class Repository:
    """restic repository class"""

    def __init__(
        self,
        uri: str,
        name: str,
        password: str | None = None,
        environment_vars: (
            dict | None
        ) = None,  # can't use field as we need to write to it during init.
    ):
        # if user did not supply any environment vars, create an empty dictionary.
        if not environment_vars:
            environment_vars = {}
        self.uri = uri
        self.name = name
        self.password = password
        self.restic_cli = ResticCli()

    @property
    def password(self) -> str:
        return self.environment_vars["RESTIC_PASSWORD"]

    @password.setter
    def password(self, value: str) -> None:
        self.environment_vars["RESTIC_PASSWORD"] = value

    def snapshots(self, json=False):
        self.restic_cli.execute(
            ["snapshots"], environment_vars=self.environment_vars, json=json
        )


@dataclass
class LocalRepository(Repository):
    """restic repository local filesystem class"""


@dataclass
class SFTPRepository(Repository):
    """restic repository sftp class"""


@dataclass
class RESTRepository(Repository):
    """restic repository sftp class"""


@dataclass
class S3Repository(Repository):
    """restic repository sftp class"""

    def __init__(
        self,
        uri: str,
        name: str,
        access_key_id: str,
        secret_access_key: str,
        session_token: str | None = None,
        password: str | None = None,
        environment_vars: (
            dict | None
        ) = None,  # can't use field as we need to write to it during init.
    ):
        # if user did not supply any environment vars, create an empty dictionary.
        if not environment_vars:
            environment_vars = {}
        super().__init__(uri, name, password, environment_vars)
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.session_token = session_token

    @property
    def access_key_id(self) -> str:
        return self.environment_vars["AWS_ACCESS_KEY_ID"]

    @access_key_id.setter
    def access_key_id(self, value: str) -> None:
        self.environment_vars["AWS_ACCESS_KEY_ID"] = value

    @property
    def secret_access_key(self) -> str:
        return self.environment_vars["AWS_SECRET_ACCESS_KEY"]

    @secret_access_key.setter
    def secret_access_key(self, value: str) -> None:
        self.environment_vars["AWS_SECRET_ACCESS_KEY"] = value

    @property
    def session_token(self) -> str:
        return self.environment_vars["AWS_SESSION_TOKEN"]

    @session_token.setter
    def session_token(self, value: str) -> None:
        self.environment_vars["AWS_SESSION_TOKEN"] = value


@dataclass
class SwiftRepository:

    def __init__():
        raise NotImplementedError


@dataclass
class B2Repository:

    def __init__():
        raise NotImplementedError


@dataclass
class AzureRepository:

    def __init__():
        raise NotImplementedError


@dataclass
class GCSRepository:

    def __init__():
        raise NotImplementedError


@dataclass
class rcloneRepository:

    def __init__():
        raise NotImplementedError
