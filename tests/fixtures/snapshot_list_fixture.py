from datetime import datetime
import pytest

from restic_replica.snapshots import SnapshotList
from tests.utils import new_snapshot


@pytest.fixture
def snapshot_list_fixture():
    return SnapshotList(
        [
            new_snapshot(datetime.fromisoformat("2023-12-31T15:19:14.968650111+01:00")),
            new_snapshot(datetime.fromisoformat("2025-04-04T15:19:14.968650111+01:00")),
            new_snapshot(datetime.fromisoformat("2025-08-31T15:19:14.968650111+01:00")),
            new_snapshot(datetime.fromisoformat("2025-09-10T15:19:14.968650111+01:00")),
            new_snapshot(datetime.fromisoformat("2025-09-14T15:19:14.968650111+01:00")),
            new_snapshot(datetime.fromisoformat("2025-09-15T15:19:14.968650111+01:00")),
            new_snapshot(datetime.fromisoformat("2025-09-20T15:19:14.968650111+01:00")),
            new_snapshot(datetime.fromisoformat("2025-09-21T07:01:42.000000000+01:00")),
            new_snapshot(datetime.fromisoformat("2025-09-21T10:34:09.000000000+01:00")),
            new_snapshot(datetime.fromisoformat("2025-09-21T15:19:14.968650111+01:00")),
        ]
    )
