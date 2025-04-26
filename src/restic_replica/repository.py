from dataclasses import dataclass, field
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
        # TODO: set env vars.
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

    def snapshots(self, json=False):
        self.restic_cli.execute(
            ["snapshots"], environment_vars=self.environment_vars, json=json
        )
