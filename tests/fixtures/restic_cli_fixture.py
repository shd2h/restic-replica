from pathlib import Path
import pytest

from restic_replica.repository import ResticCli


@pytest.fixture
def restic_cli_fixture():
    return ResticCli(
        Path("restic"), environment_vars={"RESTIC_PROGRESS_FPS": "0.016667"}
    )
