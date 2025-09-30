from collections import namedtuple
from datetime import datetime
from dataclasses import dataclass
import json
from typing import Optional, Union


@dataclass
class Policy:
    """
    Rules for filtering a list of snapshots. Behaviour should approximate that of
    `restic forget`.

    All calendar related options (daily, weekly...) work on natural time boundaries, and
    are not relative to the time the Policy is applied. Weeks are Monday 00:00 to
    Sunday 23:59, days 00:00 to 23:59, etc. They also only count days/weeks/months/etc
    which have one or more snapshots.
    """

    last: int = 0
    daily: int = 0
    weekly: int = 0
    monthly: int = 0
    yearly: int = 0

    def __post_init__(self):
        for key in self.__dict__:
            if not isinstance(self.__dict__[key], int):
                raise TypeError(f"{key} must be an integer")
            if self.__dict__[key] < 0:
                raise ValueError(f"{key} must be a non-negative integer")
        if sum(self.__dict__.values()) == 0:
            raise ValueError("Policy must contain at least one non-zero rule")


@dataclass
class Snapshot:
    """a restic snapshot"""

    time: datetime
    tree: str
    paths: list[str]
    hostname: str
    username: str
    uid: int
    gid: int
    program_version: str
    id: str
    short_id: str
    parent: Optional[str] = None  # An initial snapshot will have no parents
    original: Optional[str] = None  # present if a snapshot was rewritten
    # present if excludes were passed at backup time
    excludes: Optional[list[str]] = None
    tags: Optional[list[str]] = None  # present if snapshot has tags
    # summary was added in restic 0.17.0, so won't be included with snapshots created before then.
    summary: Optional[dict[str, Union[int | str]]] = None

    @classmethod
    def from_dict(cls, data):
        snap = cls(**data)
        # convert to timezone aware datetime object
        snap.time = datetime.fromisoformat(snap.time)
        return snap


@dataclass
class SnapshotList:
    """a list of restic snapshots"""

    snapshots: list[Snapshot]

    @classmethod
    def from_json(cls, data):
        snap_list = []
        for snap in json.loads(data):
            snap_list.append(Snapshot.from_dict(snap))
        return cls(snap_list)

    def time_sorted(self, descending=False):
        """
        Return self.snapshots by the date the snapshot was taken

        Args:
            descending: whether snapshots are sorted in descending date order (newest
                first), or ascending order (oldest first). Defaults to False (ascending),
                this matches the ordering of `restic snapshots` output.

        Returns:
            self.snapshots, sorted by the date the snapshot was taken.
        """
        return sorted(self.snapshots, key=lambda s: s.time, reverse=descending)

    def filter(self, policy: Policy):
        """
        Filter self.snapshots according to a supplied Policy.

        Args:
            policy: Policy instance that defines rules for filtering a list of Snapshots

        Returns:
            filtered_snapshots: a filtered list of snapshots
        """
        # snapshots must be sorted in descending date order for filter methods to work correctly
        sorted_snapshots = self.time_sorted(descending=True)
        filtered_snapshots = []
        # Filters are additive. Start with least restrictive filters and work down from there.
        # NB: pass in sorted_snapshots to avoid repeatedly sorting the snapshot list
        # Apply the last filter
        if policy.last:
            filtered_snapshots.extend(self._filter_last(policy.last, sorted_snapshots))
        # Apply the daily filter
        if policy.daily:
            filtered_snapshots.extend(
                self._filter_daily(policy.daily, sorted_snapshots)
            )
        # Apply the weekly filter
        if policy.weekly:
            filtered_snapshots.extend(
                self._filter_weekly(policy.weekly, sorted_snapshots)
            )
        # Apply the monthly filter
        if policy.monthly:
            filtered_snapshots.extend(
                self._filter_monthly(policy.monthly, sorted_snapshots)
            )
        # Apply the yearly filter
        if policy.yearly:
            filtered_snapshots.extend(
                self._filter_yearly(policy.yearly, sorted_snapshots)
            )

        # remove duplicates, filtering by id as that is unique per-snapshot
        # store ids for snapshots that have already been seen in a set to eliminate duplicate ids
        seen_ids = set()
        # The "or seen_ids.add()" statement ensures each snapshot id is added to the set, it always returns None (which evaluates false-y).
        filtered_snapshots = [
            s
            for s in filtered_snapshots
            if not (s.id in seen_ids or seen_ids.add(s.id))
        ]
        # sort the filtered_snapshots by date _ascending_ (to match restic output)
        return sorted(filtered_snapshots, key=lambda s: s.time, reverse=False)

    def _filter_last(self, last: int, sorted_snapshots: list[Snapshot]):
        """
        Return the most recent 'n' snapshots from sorted_snapshots.

        Args:
            last: the number of snapshots to return
            sorted_snapshots: list of snapshots, sorted in descending date order.

        Returns:
            a filtered list of snapshots
        """
        return sorted_snapshots[:last]

    def _filter_daily(self, daily: int, sorted_snapshots: list[Snapshot]):
        """
        Return the most recent 'n' snapshots from sorted_snapshots, with a maximum of
        one snapshot per calendar day.
        Note: The most _recent_ snapshot from each caldendar day will be selected.

        Args:
            daily: the number of snapshots to return
            sorted_snapshots: list of snapshots, sorted in descending date order.

        Returns:
            filtered_snapshots: a filtered list of snapshots
        """
        filtered_snapshots = []
        for snap in sorted_snapshots:
            # only process if target # of snapshots has not already been reached
            if len(filtered_snapshots) < daily:
                # datetime.isocalendar is unique on a per-day, per-year, and per-month basis.
                if snap.time.isocalendar() not in map(
                    lambda s: s.time.isocalendar(), filtered_snapshots
                ):
                    filtered_snapshots.append(snap)
        return filtered_snapshots

    def _filter_weekly(self, weekly: int, sorted_snapshots: list[Snapshot]):
        """
        Return the most recent 'n' snapshots from sorted_snapshots, with a maximum of
        one snapshot per calendar week.
        Note: The most _recent_ snapshot from each caldendar week will be selected.

        Args:
            daily: the number of snapshots to return
            sorted_snapshots: list of snapshots, sorted in descending date order.

        Returns:
            filtered_snapshots: a filtered list of snapshots
        """
        filtered_snapshots = []
        # use tuple that is unique on a per-week and per-year basis.
        YearWeek = namedtuple("YearWeek", "year week")
        for snap in sorted_snapshots:
            # only process if target # of snapshots has not already been reached
            if len(filtered_snapshots) < weekly:
                # isocalendar().week gives week # in year
                if YearWeek(snap.time.year, snap.time.isocalendar().week) not in map(
                    lambda s: YearWeek(s.time.year, s.time.isocalendar().week),
                    filtered_snapshots,
                ):
                    filtered_snapshots.append(snap)
        return filtered_snapshots

    def _filter_monthly(self, monthly: int, sorted_snapshots: list[Snapshot]):
        """
        Return the most recent 'n' snapshots from sorted_snapshots, with a maximum of
        one snapshot per calendar month.
        Note: The most _recent_ snapshot from each caldendar month will be selected.

        Args:
            daily: the number of snapshots to return
            sorted_snapshots: list of snapshots, sorted in descending date order.

        Returns:
            filtered_snapshots: a filtered list of snapshots
        """
        filtered_snapshots = []
        # use tuple that is unique on a per-month and per-year basis.
        YearMonth = namedtuple("YearMonth", "year month")
        for snap in sorted_snapshots:
            # only process if target # of snapshots has not already been reached
            if len(filtered_snapshots) < monthly:
                if YearMonth(snap.time.year, snap.time.month) not in map(
                    lambda s: YearMonth(s.time.year, s.time.month), filtered_snapshots
                ):
                    filtered_snapshots.append(snap)
        return filtered_snapshots

    def _filter_yearly(self, yearly: int, sorted_snapshots: list[Snapshot]):
        """
        Return the most recent 'n' snapshots from sorted_snapshots, with a maximum of
        one snapshot per calendar year.
        Note: The most _recent_ snapshot from each caldendar year will be selected.

        Args:
            daily: the number of snapshots to return
            sorted_snapshots: list of snapshots, sorted in descending date order.

        Returns:
            filtered_snapshots: a filtered list of snapshots
        """
        filtered_snapshots = []
        # filter only by year
        for snap in sorted_snapshots:
            # only process if target # of snapshots has not already been reached
            if len(filtered_snapshots) < yearly:
                if snap.time.year not in map(lambda s: s.time.year, filtered_snapshots):
                    filtered_snapshots.append(snap)
        return filtered_snapshots
