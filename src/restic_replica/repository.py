import copy
from dataclasses import dataclass
import logging
import os
from pathlib import Path
import subprocess
from typing import Optional, Self

logger = logging.getLogger(__name__)


@dataclass
class ResticCli:
    """
    The restic program interface

    Args:
        path: path to the restic binary
        environment_vars: dictionary of environment variables
    """

    path: Path
    environment_vars: dict[str, str]

    def _execute_live_output(self, arguments: list[str]) -> subprocess.CompletedProcess:
        """Execute the command "arguments" and write stdout/stderr from the command to logger."""
        # use Popen instead of run to get "live" output
        with subprocess.Popen(
            arguments,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="UTF-8",
            text=True,
        ) as process:
            line = None
            output = ""
            for line in process.stdout:
                if line is not None:
                    output = output + line
                    match line[0:5]:
                        case "Fatal":
                            logger.error(line.rstrip("\n"))
                        case "Warni":
                            logger.warning(line.rstrip("\n"))
                        case _:
                            logger.info(line.rstrip("\n"))
            process.wait()  # check for process termination
        # NB: restic returns code 3 if unable to read some source data during backup; this is only a partial failure.
        if process.returncode not in [0, 3]:
            raise subprocess.CalledProcessError(
                process.returncode, arguments, None, line
            )
        else:
            return subprocess.CompletedProcess(
                arguments, process.returncode, output, None
            )

    def execute(
        self,
        arguments: list[str],
        environment_vars: dict[
            str, str
        ] = {},  # NB: do not need to set to None, as the default value is only ever copied, never modified directly.
        live_output: bool = False,
        json: bool = False,
    ) -> subprocess.CompletedProcess:
        """
        Run the restic process with the provided commandline arguments.
        - If live_output, restic will write stdout/stderr to logger while the restic
        process is running.
        - If not live_output, stdout/stderr are captured and returned in a
        CompletedProcess instance after the restic process exits.

        Args:
            arguments: the commandline arguments to be passed to restic.
            environment_vars: environment variables to pass to restic.
            live_output: whether to write output to `logger` as it is emitted by restic,
                or whether to capture output and return it after the restic process exits.
            json: whether restic should emit output in json format.

        Returns:
           subprocess.CompletedProcess: the completed restic process
        """
        # ensure no mutation of mutable arguments
        local_args = copy.copy(arguments)
        local_env_vars = copy.copy(environment_vars)
        # add our environment variables to command, *overwriting duplicates*
        local_env_vars.update(self.environment_vars)
        # prepend restic binary path to args
        local_args.insert(0, str(self.path))
        # optionally add json flag
        if json:
            local_args.append("--json")
        # set environment variables
        for key, value in local_env_vars.items():
            os.environ[f"{key}"] = f"{value}"

        if live_output:
            return self._execute_live_output(local_args)
        else:
            return subprocess.run(
                local_args, capture_output=True, check=True, encoding="UTF-8", text=True
            )


@dataclass
class Repository:
    """restic repository class"""

    def __init__(
        self,
        uri: str,
        name: str,
        restic_cli: ResticCli,
        password: Optional[str] = None,
        password_file: Optional[str] = None,
        password_command: Optional[str] = None,
        environment_vars: Optional[dict] = None,
    ):
        self.uri = uri
        self.name = name
        self.restic_cli = restic_cli
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
        # TODO: support for "--insecure-no-password" to be added here, also rclone.
        # validate a password has been supplied for the repository
        self._verify_password_is_set()

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
    def password_file(self, value: Optional[str]) -> None:
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

    def snapshots(
        self, live_output: bool = False, json: bool = False
    ) -> subprocess.CompletedProcess:
        """list the snapshots stored in this repository"""

        # execute restic CLI with the snapshots argument
        args = self._common_args()
        args.extend(["snapshots"])
        return self.restic_cli.execute(
            args,
            environment_vars=self.environment_vars,
            live_output=live_output,
            json=json,
        )

    def copy(
        self, other: Self, live_output: bool = False, json: bool = False
    ) -> subprocess.CompletedProcess:
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
        return self.restic_cli.execute(
            args,
            environment_vars=self.environment_vars,
            live_output=live_output,
            json=json,
        )
