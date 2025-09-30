from contextlib import nullcontext as does_not_raise
import datetime
import pytest
import random
import textwrap
from unittest import mock

from restic_replica import snapshots
from tests.utils import new_snapshot


class TestPolicy:
    """Tests for the class repository.Policy"""

    class TestPostInit:
        """Tests for the __post_init__ method"""

        @pytest.mark.parametrize(
            "arg, expectation",
            [
                (1, does_not_raise()),
                (0, pytest.raises(ValueError)),
                (-1, pytest.raises(ValueError)),
                ("foo", pytest.raises(TypeError)),
            ],
        )
        def test_positive_int_only(self, arg, expectation):
            with expectation:
                snapshots.Policy(arg)

    class TestStr:
        """Tests for the __str__ method"""

        @pytest.mark.parametrize(
            "policy, expectation",
            [
                (snapshots.Policy(5, 0, 0, 0, 0), "keep-last=5"),
                (snapshots.Policy(0, 4, 0, 0, 0), "keep-daily=4"),
                (snapshots.Policy(0, 0, 3, 0, 0), "keep-weekly=3"),
                (snapshots.Policy(0, 0, 0, 2, 0), "keep-monthly=2"),
                (snapshots.Policy(0, 0, 0, 0, 1), "keep-yearly=1"),
                (
                    snapshots.Policy(5, 4, 3, 2, 1),
                    "keep-last=5, keep-daily=4, keep-weekly=3, keep-monthly=2, keep-yearly=1",
                ),
            ],
        )
        def test_output(self, policy, expectation):
            assert str(policy) == expectation


class TestSnapshot:
    """Tests for the class snapshots.Snapshot"""

    class TestFromDict:
        """Tests for the from_dict method"""

        def test_no_optionals(self):
            """valid snapshot should be returned if no optional parameters are specified"""
            data = {
                "time": "2025-09-22T15:19:14.968650111+01:00",
                "tree": "a9c65ce7565f9e7456606dd0119ab186ba5aefc6fb883f433e7a6b406c0f6771",
                "paths": ["/etc/hosts"],
                "hostname": "server.local",
                "username": "user",
                "uid": 1000,
                "gid": 1000,
                "program_version": "restic 0.18.0",
                "id": "13fc6fb1a3ce4ba6a693bc7e0f6f651394e0699db4c38080c2f7c1fabe5210b2",
                "short_id": "13fc6fb1",
            }

            assert snapshots.Snapshot.from_dict(data) == snapshots.Snapshot(
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
            )

        @pytest.mark.usefixtures("snapshot_fixture")
        def test_with_optionals(self, snapshot_fixture):
            """valid snapshot should be returned if any optional parameters are specified"""
            data = {
                "time": "2025-09-22T15:19:14.968650111+01:00",
                "parent": "ef699e0b81670666e639c0271b09edc6b4e3158277e3dd1c0d72809b44c468f1",
                "tree": "a9c65ce7565f9e7456606dd0119ab186ba5aefc6fb883f433e7a6b406c0f6771",
                "paths": ["/etc/hosts"],
                "hostname": "server.local",
                "username": "user",
                "uid": 1000,
                "gid": 1000,
                "excludes": ["/etc/nothosts"],
                "tags": ["rewrite"],
                "original": "e2adfd3564420f9447d42337356100a168dbf9c1de25b3086fbdc9c4a18ba4a1",
                "program_version": "restic 0.18.0",
                "summary": {
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
                "id": "13fc6fb1a3ce4ba6a693bc7e0f6f651394e0699db4c38080c2f7c1fabe5210b2",
                "short_id": "13fc6fb1",
            }
            assert snapshots.Snapshot.from_dict(data) == snapshot_fixture


class TestSnapshotList:
    """Tests for the class snapshots.SnapshotList"""

    class TestFromJson:
        """Tests for the from_json method"""

        @pytest.mark.usefixtures("snapshot_fixture")
        def test_ingest(self, snapshot_fixture):
            """json should be parsed and return valid snapshotlist and snapshot instances"""
            data = textwrap.dedent(
                # fmt: off
                "["
                    "{"
                        '"time":"2025-09-22T15:19:14.968650111+01:00",'
                        '"parent": "ef699e0b81670666e639c0271b09edc6b4e3158277e3dd1c0d72809b44c468f1",'
                        '"tree":"a9c65ce7565f9e7456606dd0119ab186ba5aefc6fb883f433e7a6b406c0f6771",'
                        '"paths":["/etc/hosts"],'
                        '"hostname":"server.local",'
                        '"username":"user",'
                        '"uid":1000,'
                        '"gid":1000,'
                        '"excludes": ["/etc/nothosts"],'
                        '"tags": ["rewrite"],'
                        '"original": "e2adfd3564420f9447d42337356100a168dbf9c1de25b3086fbdc9c4a18ba4a1",'
                        '"program_version":"restic 0.18.0",'
                        '"summary": {'
                            '"backup_start": "2025-09-22T15:19:14.968650111+01:00",'
                            '"backup_end": "2025-09-22T15:19:15.693199959+01:00",'
                            '"files_new": 1,'
                            '"files_changed": 0,'
                            '"files_unmodified": 0,'
                            '"dirs_new": 1,'
                            '"dirs_changed": 0,'
                            '"dirs_unmodified": 0,'
                            '"data_blobs": 1,'
                            '"tree_blobs": 2,'
                            '"data_added": 1288,'
                            '"data_added_packed": 1028,'
                            '"total_files_processed": 1,'
                            '"total_bytes_processed": 384'
                        "},"
                        '"id":"13fc6fb1a3ce4ba6a693bc7e0f6f651394e0699db4c38080c2f7c1fabe5210b2",'
                        '"short_id":"13fc6fb1"'
                    "}"
                "]"
                # fmt: on
            )
            assert snapshots.SnapshotList.from_json(data).snapshots == [
                snapshot_fixture
            ]

        def test_null_ingest(self):
            """empty json data should return an empty snapshotlist instance"""
            data = "[]"
            assert snapshots.SnapshotList.from_json(data).snapshots == []

    class TestTimeSorted:
        """Tests for the time_sorted method"""

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_sort_ascending(self, snapshot_list_fixture):
            """snapshots should be sorted by date ascending"""
            random.shuffle(snapshot_list_fixture.snapshots)
            sorted = snapshot_list_fixture.time_sorted(descending=False)
            for i, snap in enumerate(sorted):
                if i != 0:
                    assert snap.time > sorted[i - 1].time

        def test_sort_descending(self, snapshot_list_fixture):
            """snapshots should be sorted by date descending"""
            random.shuffle(snapshot_list_fixture.snapshots)
            sorted = snapshot_list_fixture.time_sorted(descending=True)
            for i, snap in enumerate(sorted):
                if i != 0:
                    assert snap.time < sorted[i - 1].time

    class TestFilter:
        """Tests for the filter method"""

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_no_snapshots(self, snapshot_list_fixture):
            """if no filters return any snapshots, then no snapshots should be returned"""
            # snapshot_list_fixture has 10 snapshots
            # set a policy that will return nothing
            policy = snapshots.Policy(1, 0, 0, 0, 0)
            # set "last" to zero after init, to avoid triggering "all zeroes not allowed" check
            policy.last = 0
            assert snapshot_list_fixture.filter(policy) == []

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_first_sort(self, snapshot_list_fixture):
            """snapshots should be sorted into descending order of time before being passed to _filter* functions"""
            # policy.last set to non-zero value, so _filter_last will trigger
            policy = snapshots.Policy(99999, 0, 0, 0, 0)
            with mock.patch.object(
                snapshot_list_fixture, "_filter_last", return_value=[]
            ) as target:
                snapshot_list_fixture.filter(policy)
            # assert that filter_last was called with the snapshots list sorted in reverse
            target.assert_called_with(
                policy.last, list(reversed(snapshot_list_fixture.snapshots))
            )

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_return_sort(self, snapshot_list_fixture):
            """snapshots should be sorted into ascending order when returned"""
            # invert the snapshot list, so it is sorted in reverse
            snap_list = list(reversed(snapshot_list_fixture.snapshots))
            # policy.last set to non-zero value, so _filter_last will trigger
            policy = snapshots.Policy(1, 0, 0, 0, 0)
            # filter_last mocked to return reversed snapshot list
            with mock.patch.object(
                snapshot_list_fixture, "_filter_last", return_value=snap_list
            ):
                # output should be sorted into ascending order again
                assert (
                    snapshot_list_fixture.filter(policy)
                    == snapshot_list_fixture.snapshots
                )

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_filters_merge(self, snapshot_list_fixture, monkeypatch):
            """snapshots selected by each filter should all be combined into the output"""

            def new_snaps(*args, **kwargs):
                return [new_snapshot(datetime.date(2025, 9, 29))]

            # enable all filters, by setting to non-zero value
            policy = snapshots.Policy(1, 1, 1, 1, 1)
            # mock all filters to return unqiue snapshots
            monkeypatch.setattr(snapshot_list_fixture, "_filter_last", new_snaps)
            monkeypatch.setattr(snapshot_list_fixture, "_filter_daily", new_snaps)
            monkeypatch.setattr(snapshot_list_fixture, "_filter_weekly", new_snaps)
            monkeypatch.setattr(snapshot_list_fixture, "_filter_monthly", new_snaps)
            monkeypatch.setattr(snapshot_list_fixture, "_filter_yearly", new_snaps)
            # verify 5 snapshots are in the output
            assert len(snapshot_list_fixture.filter(policy)) == 5

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_no_duplicates(self, snapshot_list_fixture):
            """snapshots which are selected by multiple filters should only appear once in the output"""
            # each filter will select one snapshot (the most recent)
            policy = snapshots.Policy(1, 1, 1, 1, 1)
            expected = snapshot_list_fixture.snapshots[-1]
            assert snapshot_list_fixture.filter(policy) == [expected]

    class TestFilterLast:
        """Tests for the _filter_last method"""

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_no_snapshots(self, snapshot_list_fixture):
            """an empty list of snapshots should return an empty list"""
            assert snapshot_list_fixture._filter_last(5, []) == []

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_some_snapshots(self, snapshot_list_fixture):
            """the requested number of snapshots should be returned, from the top of the list"""
            snap_list = snapshot_list_fixture.snapshots
            assert (
                snapshot_list_fixture._filter_last(3, snap_list)
                == snapshot_list_fixture.snapshots[:3]
            )

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_not_enough_snapshots(self, snapshot_list_fixture):
            """if more than the total number of snapshots are requested, the entire list should be returned"""
            # snapshot_list_fixture has 10 total snapshots
            snap_list = snapshot_list_fixture.snapshots
            assert len(snapshot_list_fixture._filter_last(20, snap_list)) == 10

    class TestFilterDaily:
        """Tests for the _filter_daily method"""

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_zero(self, snapshot_list_fixture):
            """requesting zero snapshots should return an empty list"""
            snap_list = snapshot_list_fixture.snapshots
            assert snapshot_list_fixture._filter_daily(0, snap_list) == []

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_sequential_days(self, snapshot_list_fixture):
            """snapshots on sequential days should be returned up to the requested number"""
            snap_list = [
                new_snapshot(datetime.date(2025, 9, 21)),
                new_snapshot(datetime.date(2025, 9, 20)),
                new_snapshot(datetime.date(2025, 9, 19)),
                new_snapshot(datetime.date(2025, 9, 18)),
            ]

            assert snapshot_list_fixture._filter_daily(3, snap_list) == snap_list[:3]

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_non_sequential_days(self, snapshot_list_fixture):
            """snapshots on non-sequential days should be returned up to the requested number"""
            snap_list = [
                new_snapshot(datetime.date(2025, 9, 21)),
                new_snapshot(datetime.date(2025, 9, 19)),
                new_snapshot(datetime.date(2025, 9, 18)),
                new_snapshot(datetime.date(2025, 9, 17)),
            ]
            assert snapshot_list_fixture._filter_daily(3, snap_list) == snap_list[:3]

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_max_one_per_day(self, snapshot_list_fixture):
            """only the most recent snapshot on any given calendar day should be considered"""
            snap_list = [
                new_snapshot(datetime.datetime(2025, 9, 21, 15, 19, 14)),
                new_snapshot(datetime.datetime(2025, 9, 21, 10, 34, 9)),
                new_snapshot(datetime.datetime(2025, 9, 21, 7, 1, 42)),
                new_snapshot(datetime.date(2025, 9, 20)),
                new_snapshot(datetime.date(2025, 9, 19)),
            ]
            assert snapshot_list_fixture._filter_daily(3, snap_list) == [
                snap_list[0],
                snap_list[3],
                snap_list[4],
            ]

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_week_boundary(self, snapshot_list_fixture):
            """snapshots should be able to span the week boundary without issue"""
            snap_list = [
                new_snapshot(datetime.date(2025, 9, 23)),
                new_snapshot(datetime.date(2025, 9, 22)),  # monday
                new_snapshot(datetime.date(2025, 9, 21)),  # sunday
                new_snapshot(datetime.date(2025, 9, 20)),
            ]

            assert snapshot_list_fixture._filter_daily(3, snap_list) == snap_list[:3]

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_month_boundary(self, snapshot_list_fixture):
            """snapshots should be able to span the month boundary without issue"""
            snap_list = [
                new_snapshot(datetime.date(2025, 9, 23)),
                new_snapshot(datetime.date(2025, 9, 22)),
                new_snapshot(datetime.date(2025, 8, 23)),
                new_snapshot(datetime.date(2025, 8, 22)),
            ]
            assert snapshot_list_fixture._filter_daily(3, snap_list) == snap_list[:3]

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_year_boundary(self, snapshot_list_fixture):
            """snapshots should be able to span the year boundary without issue"""
            snap_list = [
                new_snapshot(datetime.date(2025, 9, 23)),
                new_snapshot(datetime.date(2025, 9, 22)),
                new_snapshot(datetime.date(2024, 9, 23)),
                new_snapshot(datetime.date(2024, 9, 22)),
            ]
            assert snapshot_list_fixture._filter_daily(3, snap_list) == snap_list[:3]

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_not_enough_snapshots(self, snapshot_list_fixture):
            """if more than the total number of daily snapshots are requested, all daily snapshots should be returned"""
            # snapshot_list_fixture has three snapshots from a single day, out of 10 total
            snap_list = snapshot_list_fixture.snapshots
            assert len(snapshot_list_fixture._filter_daily(10, snap_list)) == 8

    class TestFilterWeekly:
        """Tests for the _filter_weekly method"""

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_zero(self, snapshot_list_fixture):
            """requesting zero snapshots should return an empty list"""
            snap_list = snapshot_list_fixture.snapshots
            assert snapshot_list_fixture._filter_weekly(0, snap_list) == []

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_sequential_weeks(self, snapshot_list_fixture):
            """snapshots on sequential weeks should be returned up to the requested number"""
            snap_list = [
                new_snapshot(datetime.date(2025, 9, 29)),
                new_snapshot(datetime.date(2025, 9, 22)),
                new_snapshot(datetime.date(2025, 9, 15)),
                new_snapshot(datetime.date(2025, 9, 8)),
            ]

            assert snapshot_list_fixture._filter_weekly(3, snap_list) == snap_list[:3]

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_non_sequential_weeks(self, snapshot_list_fixture):
            """snapshots on non-sequential weeks should be returned up to the requested number"""
            snap_list = [
                new_snapshot(datetime.date(2025, 9, 29)),
                new_snapshot(datetime.date(2025, 9, 15)),
                new_snapshot(datetime.date(2025, 9, 8)),
                new_snapshot(datetime.date(2025, 9, 1)),
            ]
            assert snapshot_list_fixture._filter_weekly(3, snap_list) == snap_list[:3]

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_max_one_per_week(self, snapshot_list_fixture):
            """only the most recent snapshot from any given calendar week should be considered"""
            snap_list = [
                new_snapshot(datetime.date(2025, 9, 30)),  # week 4
                new_snapshot(datetime.date(2025, 9, 28)),  # week 3
                new_snapshot(datetime.date(2025, 9, 25)),  # week 3
                new_snapshot(datetime.date(2025, 9, 22)),  # week 3
                new_snapshot(datetime.date(2025, 9, 21)),  # week 2
            ]
            assert snapshot_list_fixture._filter_weekly(3, snap_list) == [
                snap_list[0],
                snap_list[1],
                snap_list[4],
            ]

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_month_boundary(self, snapshot_list_fixture):
            """snapshots should be able to span the month boundary without issue"""
            snap_list = [
                new_snapshot(datetime.date(2025, 9, 23)),
                new_snapshot(datetime.date(2025, 9, 10)),
                new_snapshot(datetime.date(2025, 8, 23)),
                new_snapshot(datetime.date(2025, 8, 10)),
            ]
            assert snapshot_list_fixture._filter_weekly(3, snap_list) == snap_list[:3]

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_year_boundary(self, snapshot_list_fixture):
            """snapshots should be able to span the year boundary without issue"""
            snap_list = [
                new_snapshot(datetime.date(2025, 9, 23)),
                new_snapshot(datetime.date(2025, 9, 10)),
                new_snapshot(datetime.date(2024, 9, 23)),
                new_snapshot(datetime.date(2024, 9, 10)),
            ]
            assert snapshot_list_fixture._filter_weekly(3, snap_list) == snap_list[:3]

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_not_enough_snapshots(self, snapshot_list_fixture):
            """if more than the total number of weekly snapshots are requested, all weekly snapshots should be returned"""
            # snapshot_list_fixture has 5 snapshots from unique weeks, out of 10 total
            snap_list = snapshot_list_fixture.snapshots
            assert len(snapshot_list_fixture._filter_weekly(10, snap_list)) == 5

    class TestFilterMonthly:
        """Tests for the _filter_monthly method"""

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_zero(self, snapshot_list_fixture):
            """requesting zero snapshots should return an empty list"""
            snap_list = snapshot_list_fixture.snapshots
            assert snapshot_list_fixture._filter_monthly(0, snap_list) == []

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_sequential_months(self, snapshot_list_fixture):
            """snapshots on sequential months should be returned up to the requested number"""
            snap_list = [
                new_snapshot(datetime.date(2025, 9, 29)),
                new_snapshot(datetime.date(2025, 8, 11)),
                new_snapshot(datetime.date(2025, 7, 6)),
                new_snapshot(datetime.date(2025, 5, 31)),
            ]

            assert snapshot_list_fixture._filter_monthly(3, snap_list) == snap_list[:3]

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_non_sequential_months(self, snapshot_list_fixture):
            """snapshots on non-sequential months should be returned up to the requested number"""
            snap_list = [
                new_snapshot(datetime.date(2025, 9, 29)),
                new_snapshot(datetime.date(2025, 5, 31)),
                new_snapshot(datetime.date(2025, 4, 19)),
                new_snapshot(datetime.date(2025, 3, 1)),
            ]
            assert snapshot_list_fixture._filter_monthly(3, snap_list) == snap_list[:3]

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_max_one_per_month(self, snapshot_list_fixture):
            """only the most recent snapshot from any given calendar month should be considered"""
            snap_list = [
                new_snapshot(datetime.date(2025, 9, 30)),
                new_snapshot(datetime.date(2025, 9, 28)),
                new_snapshot(datetime.date(2025, 9, 25)),
                new_snapshot(datetime.date(2025, 8, 11)),
                new_snapshot(datetime.date(2025, 7, 6)),
            ]
            assert snapshot_list_fixture._filter_monthly(3, snap_list) == [
                snap_list[0],
                snap_list[3],
                snap_list[4],
            ]

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_year_boundary(self, snapshot_list_fixture):
            """snapshots should be able to span the year boundary without issue"""
            snap_list = [
                new_snapshot(datetime.date(2025, 9, 23)),
                new_snapshot(datetime.date(2025, 8, 11)),
                new_snapshot(datetime.date(2024, 9, 23)),
                new_snapshot(datetime.date(2024, 8, 11)),
            ]
            assert snapshot_list_fixture._filter_monthly(3, snap_list) == snap_list[:3]

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_not_enough_snapshots(self, snapshot_list_fixture):
            """if more than the total number of monthly snapshots are requested, all monthly snapshots should be returned"""
            # snapshot_list_fixture has 4 snapshots from unique months, out of 10 total
            snap_list = snapshot_list_fixture.snapshots
            assert len(snapshot_list_fixture._filter_monthly(10, snap_list)) == 4

    class TestFilterYearly:
        """Tests for the _filter_yearly method"""

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_zero(self, snapshot_list_fixture):
            """requesting zero snapshots should return an empty list"""
            snap_list = snapshot_list_fixture.snapshots
            assert snapshot_list_fixture._filter_yearly(0, snap_list) == []

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_sequential_years(self, snapshot_list_fixture):
            """snapshots on sequential years should be returned up to the requested number"""
            snap_list = [
                new_snapshot(datetime.date(2025, 9, 29)),
                new_snapshot(datetime.date(2024, 9, 23)),
                new_snapshot(datetime.date(2023, 7, 6)),
                new_snapshot(datetime.date(2022, 5, 31)),
            ]

            assert snapshot_list_fixture._filter_yearly(3, snap_list) == snap_list[:3]

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_non_sequential_years(self, snapshot_list_fixture):
            """snapshots on non-sequential years should be returned up to the requested number"""
            snap_list = [
                new_snapshot(datetime.date(2025, 9, 29)),
                new_snapshot(datetime.date(2022, 5, 31)),
                new_snapshot(datetime.date(2021, 3, 4)),
                new_snapshot(datetime.date(2020, 11, 15)),
            ]
            assert snapshot_list_fixture._filter_yearly(3, snap_list) == snap_list[:3]

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_max_one_per_year(self, snapshot_list_fixture):
            """only the most recent snapshot from any given calendar year should be considered"""
            snap_list = [
                new_snapshot(datetime.date(2025, 9, 30)),
                new_snapshot(datetime.date(2025, 8, 11)),
                new_snapshot(datetime.date(2025, 7, 6)),
                new_snapshot(datetime.date(2024, 9, 23)),
                new_snapshot(datetime.date(2023, 7, 6)),
            ]
            assert snapshot_list_fixture._filter_yearly(3, snap_list) == [
                snap_list[0],
                snap_list[3],
                snap_list[4],
            ]

        @pytest.mark.usefixtures("snapshot_list_fixture")
        def test_not_enough_snapshots(self, snapshot_list_fixture):
            """if more than the total number of yearly snapshots are requested, all yearly snapshots should be returned"""
            # snapshot_list_fixture has 2 snapshots from unique years, out of 10 total
            snap_list = snapshot_list_fixture.snapshots
            assert len(snapshot_list_fixture._filter_yearly(10, snap_list)) == 2
