from datetime import datetime
import random
import string

from restic_replica.snapshots import Snapshot


def new_snapshot(timestamp: datetime):
    id = "".join(
        random.choice(string.ascii_lowercase + string.digits) for _ in range(64)
    )
    short_id = id[:8]
    return Snapshot(
        timestamp,
        "a9c65ce7565f9e7456606dd0119ab186ba5aefc6fb883f433e7a6b406c0f6771",
        ["/etc/hosts"],
        "server.local",
        "user",
        1000,
        1000,
        "restic 0.16.4",
        id,
        short_id,
    )
