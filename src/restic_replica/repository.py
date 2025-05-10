from dataclasses import dataclass, field
import logging
import os
from pathlib import Path
import subprocess
from typing import Self

logger = logging.getLogger(__name__)


@dataclass
class ResticCli:
    """restic binary"""

    # TODO: need to get these from the config file.
    binary: Path = Path("/usr/local/bin/restic")
    environment_vars = {"RESTIC_PROGRESS_FPS": "0.003333"}

    def execute(self, arguments: list, environment_vars={}, json=False):
        # add restic binary to args
        arguments.insert(0, str(self.binary))
        # add json flag
        if json:
            arguments.append("--json")
        # concat env vars
        environment_vars.update(self.environment_vars)
        # set env vars
        for key, value in environment_vars.items():
            os.environ[f"{key}"] = f"{value}"
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
        args = self._common_args().extend(["copy", "--from-repository", other.uri])
        self.restic_cli.execute(args, environment_vars=self.environment_vars, json=json)
