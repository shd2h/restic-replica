import datetime
import pytest

from restic_replica.snapshots import Snapshot


@pytest.fixture
def snapshot_fixture():
    """return a (class:`snapshots.Snapshot`) instance"""
    return Snapshot(
        datetime.datetime(
            2025,
            9,
            22,
            15,
            19,
            14,
            968650,
            tzinfo=datetime.timezone(datetime.timedelta(seconds=3600)),
        ),
        "a9c65ce7565f9e7456606dd0119ab186ba5aefc6fb883f433e7a6b406c0f6771",
        ["/etc/hosts"],
        "server.local",
        "user",
        1000,
        1000,
        "restic 0.18.0",
        "13fc6fb1a3ce4ba6a693bc7e0f6f651394e0699db4c38080c2f7c1fabe5210b2",
        "13fc6fb1",
        parent="ef699e0b81670666e639c0271b09edc6b4e3158277e3dd1c0d72809b44c468f1",
        original="e2adfd3564420f9447d42337356100a168dbf9c1de25b3086fbdc9c4a18ba4a1",
        excludes=["/etc/nothosts"],
        tags=["rewrite"],
        summary={
            "backup_start": "2025-09-22T15:19:14.968650111+01:00",
            "backup_end": "2025-09-22T15:19:15.693199959+01:00",
            "files_new": 1,
            "files_changed": 0,
            "files_unmodified": 0,
            "dirs_new": 1,
            "dirs_changed": 0,
            "dirs_unmodified": 0,
            "data_blobs": 1,
            "tree_blobs": 2,
            "data_added": 1288,
            "data_added_packed": 1028,
            "total_files_processed": 1,
            "total_bytes_processed": 384,
        },
    )
