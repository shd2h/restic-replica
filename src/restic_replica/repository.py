from dataclasses import dataclass
from pathlib import Path


@dataclass
class Repository:
    """restic repository class"""

    name: str
    password: str
    environment_vars = []
    # TODO: raw_string is going to be the repository URI.
    # raw_string: str


@dataclass
class LocalRepository(Repository):
    """restic repository local filesystem class"""

    path: Path
    type: str = "local"


@dataclass
class SFTPRepository(Repository):
    """restic repository sftp class"""

    username: str
    # TODO: ip addr?
    hostname: str
    port: int
    type: str = "sftp"
