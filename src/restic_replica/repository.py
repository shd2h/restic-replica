from copy import deepcopy
from dataclasses import dataclass
import logging
import os
from pathlib import Path
import subprocess
from typing import Optional, Self, Union

logger = logging.getLogger(__name__)


@dataclass
class ResticCli:
    """restic binary"""

    # TODO: need to get these from the config file.
    binary: Path = Path("/usr/local/bin/restic")
    environment_vars = {"RESTIC_PROGRESS_FPS": "0.003333"}

    # TODO: implement json/non-live output
    def execute(self, arguments: list, environment_vars={}, json=False) -> int:
        # ensure no mutation of mutable arguments
        local_args = deepcopy(arguments)
        local_env_vars = deepcopy(environment_vars)
        # add our environment variables to command
        local_env_vars.update(self.environment_vars)
        # prepend restic binary path to args
        local_args.insert(0, str(self.binary))
        # optionally add json flag
        if json:
            local_args.append("--json")
        # set environment variables
        for key, value in local_env_vars.items():
            os.environ[f"{key}"] = f"{value}"
        # use Popen instead of run to get "live" output
        with subprocess.Popen(
            local_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        ) as process:
            for line_raw in process.stdout:
                line = line_raw.decode("utf-8").rstrip("\n")
                if line is not None:
                    match line[0:5]:
                        case "Fatal":
                            logger.critical(line)
                        case "Error":
                            logger.error(line)
                        case "Warni":
                            logger.warning(line)
                        case "Debug":
                            logger.debug(line)
                        case _:
                            logger.info(line)
            process.wait()  # check for process termination
        if process.returncode != 0:
            raise subprocess.CalledProcessError(
                process.returncode, " ".join(local_args), line
            )
        else:
            return process.stdout


@dataclass
class Repository:
    """restic repository class"""

    def __init__(
        self,
        uri: str,
        name: str,
        password: Optional[str] = None,
        password_file: Optional[Union[str | Path]] = None,
        password_command: Optional[str] = None,
        environment_vars: dict = None,
    ):
        self.uri = uri
        self.name = name
        if environment_vars is None:
            self.environment_vars = {}
        else:
            self.environment_vars = environment_vars
        # any supplied passwords overwrite env vars, match restic behaviour of supplied cli arguments having precedence
        if password is not None:
            self.password = password
        if password_file is not None:
            self.password_file = password_file
        if password_command is not None:
            self.password_command = password_command
        # TODO: support for "--insecure-no-password" to be added here.
        # validate a password has been supplied for the repository
        self._verify_password_is_set()
        self.restic_cli = ResticCli()

    @property
    def password(self) -> Optional[str]:
        try:
            return self.environment_vars["RESTIC_PASSWORD"]
        except KeyError:
            return None

    @password.setter
    def password(self, value: Optional[str]) -> None:
        self.environment_vars["RESTIC_PASSWORD"] = value

    @property
    def password_file(self) -> Optional[str]:
        try:
            return self.environment_vars["RESTIC_PASSWORD_FILE"]
        except KeyError:
            return None

    @password_file.setter
    def password_file(self, value: Optional[Union[str | Path]]) -> None:
        # explicitly cast Path to str (this would happen implicitly otherwise)
        if isinstance(value, Path):
            self.environment_vars["RESTIC_PASSWORD_FILE"] = str(value)
        else:
            self.environment_vars["RESTIC_PASSWORD_FILE"] = value

    @property
    def password_command(self) -> Optional[str]:
        try:
            return self.environment_vars["RESTIC_PASSWORD_COMMAND"]
        except KeyError:
            return None

    @password_command.setter
    def password_command(self, value: Optional[str]) -> None:
        self.environment_vars["RESTIC_PASSWORD_COMMAND"] = value

    def __str__(self):
        return self.uri

    def _common_args(self):
        return ["-r", f"{self.uri}"]

    def _verify_password_is_set(self) -> bool:
        """Assert that the password options supplied are valid"""
        # Attempt to mimic restics behaviour here, in that:
        # - password_file or password_command overwrite password
        # - password_file and password_command are mutually exclusive

        # check at least one password* option was supplied
        if not (self.password or self.password_file or self.password_command):
            raise ValueError(
                "one password argument is required: password, password_file, or password_command"
            )
        # check password_file and password_command were not both supplied.
        if self.password_file and self.password_command:
            raise KeyError("password_file and password_command are mutually exclusive")
        # print warning if password option will be overwritten; password-file and password-command take priority in restic
        if self.password and self.password_file:
            logger.warning(
                f"password and password_file were specified for repository {self.uri}; password_file will be used"
            )
        if self.password and self.password_command:
            logger.warning(
                f"password and password_command were specified for repository {self.uri}; password_command will be used"
            )
        return True

    # TODO: implement json/non-live output
    def snapshots(self, json=False) -> bool:
        """list the snapshots stored in this repository"""

        # execute restic CLI with the snapshots argument
        args = self._common_args()
        args.extend(["snapshots"])
        rc = self.restic_cli.execute(
            args, environment_vars=self.environment_vars, json=json
        )
        return rc == 0

    # TODO: implement json/non-live output
    def copy(self, other: Self, json=False) -> bool:
        """copy snapshots from other repository to this repository"""

        # prevent copying to/from the same repository
        if other.uri == self.uri:
            raise RuntimeError("source and destination repository must be different")

        # Set environment variables based on the password configuration of the other repository, in descending order of primacy
        if other.password_command:
            self.environment_vars["RESTIC_FROM_PASSWORD_COMMAND"] = (
                other.password_command
            )
        elif other.password_file:
            self.environment_vars["RESTIC_FROM_PASSWORD_FILE"] = other.password_file
        else:  # if neither a password command or password file were supplied, use password.
            self.environment_vars["RESTIC_FROM_PASSWORD"] = other.password

        # execute restic CLI with the copy and other repository argument
        args = self._common_args()
        args.extend(["copy", "--from-repo", other.uri])
        rc = self.restic_cli.execute(
            args, environment_vars=self.environment_vars, json=json
        )
        return rc == 0
