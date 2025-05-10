from copy import deepcopy
from dataclasses import dataclass, field
import logging
import os
from pathlib import Path
import subprocess
from typing import Optional, Self

logger = logging.getLogger(__name__)


@dataclass
class ResticCli:
    """restic binary"""

    # TODO: need to get these from the config file.
    binary: Path = Path("/usr/local/bin/restic")
    environment_vars = {"RESTIC_PROGRESS_FPS": "0.003333"}

    def execute(self, arguments: list, environment_vars={}, json=False):
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
            for line in process.stdout:
                logger.info(line.decode("utf-8").rstrip("\n"))
            process.wait()  # check for process termination
        if process.returncode != 0:
            raise subprocess.CalledProcessError(
                process.returncode, " ".join(local_args), line
            )


@dataclass
class Repository:
    """restic repository class"""

    def __init__(
        self,
        uri: str,
        name: str,
        password: Optional[str] = None,
        environment_vars: dict = field(default_factory=dict),
    ):
        self.uri = uri
        self.name = name
        self.environment_vars = environment_vars
        if password:
            self.password = password
        self.restic_cli = ResticCli()

    @property
    def password(self) -> str:
        return self.environment_vars["RESTIC_PASSWORD"]

    @password.setter
    def password(self, value: str) -> None:
        self.environment_vars["RESTIC_PASSWORD"] = value

    def __str__(self):
        return self.uri

    def _common_args(self):
        return ["-r", f"{self.uri}"]

    def snapshots(self, json=False):
        args = self._common_args()
        args.extend(["snapshots"])
        self.restic_cli.execute(args, environment_vars=self.environment_vars, json=json)

    def copy(self, other: Self, json=False):
        """copy snapshots from other to self"""
        if other.password:
            self.environment_vars["RESTIC_FROM_PASSWORD"] = other.password
        args = self._common_args()
        args.extend(["copy", "--from-repository", other.uri])
        self.restic_cli.execute(args, environment_vars=self.environment_vars, json=json)
