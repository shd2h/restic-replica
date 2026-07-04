import importlib.resources
from pathlib import Path
import pytest
from subprocess import CalledProcessError, CompletedProcess
import textwrap
import tomllib
from unittest import mock

from restic_replica import __assets__, app
from restic_replica.repository import Repository, ResticCli
from restic_replica.snapshots import (
    Policy,
    SnapshotList,
    SnapshotFilterOptions,
    SnapshotGroupByOptions,
)


class TestEnsureConfigFile:
    """Tests for the function app.ensure_config_file"""

    def test_existing_config_file(self, tmp_path):
        """
        if a path to a config file is supplied, and the file exists, the path to the
        file should be returned.
        """
        assert app.ensure_config_file(tmp_path) == tmp_path

    @mock.patch("pathlib.Path.exists", return_value=True)
    @mock.patch("platform.system", return_value="Linux")
    def test_existing_default_config_file_nonwin(self, *args):
        """
        if no path to a config file is supplied, and the platform is non-windows, and
        the default config file exists, the default config file path for non-windows
        should be returned.
        """
        assert app.ensure_config_file() == Path.home() / ".restic-replica/config.toml"

    @mock.patch("pathlib.Path.exists", return_value=True)
    @mock.patch("platform.system", return_value="Windows")
    def test_existing_default_config_file_win(self, *args):
        """
        if no path to a config file is supplied, and the platform is windows, and the
        default config file exists, the default config file path for windows should be
        returned.
        """
        assert (
            app.ensure_config_file()
            == Path.home() / "AppData/Local/restic-replica/config.toml"
        )

    @mock.patch("pathlib.Path.exists", return_value=False)
    @mock.patch("platform.system", return_value="Linux")
    @mock.patch("pathlib.Path.mkdir", return_value=None)
    @mock.patch("shutil.copyfile", return_value=None)
    def test_default_config_file_path_nonwin(self, *args):
        """
        if no path to a config file is supplied, and the platform is non-windows, and
        the default config file does not exist, a SystemExit exception should be raised.
        """
        with pytest.raises(SystemExit):
            app.ensure_config_file()
        args[0].assert_called_with(
            importlib.resources.files(__assets__) / "example_config.toml",
            Path.home() / ".restic-replica/config.toml",
        )

    @mock.patch("pathlib.Path.exists", return_value=False)
    @mock.patch("platform.system", return_value="Windows")
    @mock.patch("pathlib.Path.mkdir", return_value=None)
    @mock.patch("shutil.copyfile", return_value=None)
    def test_default_config_file_path_win(self, *args):
        """
        if no path to a config file is supplied, and the platform is windows, and the
        default config file does not exist, a SystemExit exception should be raised.
        """
        with pytest.raises(SystemExit):
            app.ensure_config_file()
        args[0].assert_called_with(
            importlib.resources.files(__assets__) / "example_config_win.toml",
            Path.home() / "AppData/Local/restic-replica/config.toml",
        )

    @mock.patch("platform.system", return_value="Linux")
    @mock.patch("pathlib.Path.mkdir", return_value=None)
    @mock.patch("shutil.copyfile", return_value=None)
    def test_missing_config_file(self, *args):
        """
        if a path to a config file is supplied, and the file does not exist, a
        SystemExit exception should be raised.
        """
        target = Path("/not/a/real/path")
        with pytest.raises(SystemExit):
            app.ensure_config_file(target)
        args[0].assert_called_with(
            importlib.resources.files(__assets__) / "example_config.toml",
            target,
        )


class TestReadConfigFile:
    """Tests for the function app.read_config_file"""

    def test_valid_toml(self, tmp_path):
        """Valid toml should load into a dictionary correctly"""
        good_toml = textwrap.dedent(
            """\
            [app]
            restic_binary = "/usr/local/bin/restic"
            
            [source]
            repository_uri = "/tmp/restic-repo"
            password = "secret"
        """
        )
        expected_result = {
            "app": {"restic_binary": "/usr/local/bin/restic"},
            "source": {"repository_uri": "/tmp/restic-repo", "password": "secret"},
        }
        f = tmp_path / "good.toml"
        f.write_text(good_toml, encoding="utf-8")
        assert app.read_config_file(f) == expected_result

    def test_invalid_toml(self, tmp_path):
        """Invalid toml should raise TOMLDecodeError"""
        bad_toml = textwrap.dedent(
            """\
            [app]
            restic_binary = "/usr/local/bin/restic
            
            [source
            repository_uri = "/tmp/restic-repo"
            password = "secret"
        """
        )
        f = tmp_path / "bad.toml"
        f.write_text(bad_toml, encoding="utf-8")
        with pytest.raises(tomllib.TOMLDecodeError):
            app.read_config_file(f)

    def test_missing_file(self, tmp_path):
        """An invalid/nonexistent file path should raise a FileNotFoundError"""
        f = tmp_path / "notarealfile.toml"
        with pytest.raises(FileNotFoundError):
            app.read_config_file(f)


class TestGetLogdir:
    """Tests for the function app.get_logdir"""

    def test_provided_logdir(self):
        """A log directory path should be returned if one is provided"""
        assert app.get_logdir(
            {"app": {"log_directory": "/var/log/restic-replica/"}}
        ) == Path("/var/log/restic-replica/")

    def test_provided_logdir_tilde(self):
        """If tilde is used in the directory path, it should be expanded"""
        assert app.get_logdir({"app": {"log_directory": "~/.restic-replica/"}}) == Path(
            Path.home() / ".restic-replica/"
        )

    def test_missing_logdir_nonwin(self):
        """The default log directory for not-windows should be returned if no log directory is provided"""
        with mock.patch("platform.system", return_value="Linux"):
            assert app.get_logdir({}) == Path.home() / ".restic-replica"

    def test_missing_logdir_windows(self):
        """The default log directory for windows should be returned if no log directory is provided"""
        with mock.patch("platform.system", return_value="Windows"):
            assert app.get_logdir({}) == Path.home() / "AppData/Local/restic-replica"


class TestGetRestic:
    """Tests for the function app.get_restic"""

    def test_defaults_nonwin(self):
        """Default configuration for not-windows should be set if no arguments are supplied"""
        with mock.patch("platform.system", return_value="Linux"):
            assert app.get_restic({}) == ResticCli(
                Path("restic"), {"RESTIC_PROGRESS_FPS": "0.016667"}
            )

    def test_defaults_win(self):
        """Default configuration for windows should be set if no arguments are supplied"""
        with mock.patch("platform.system", return_value="Windows"):
            assert app.get_restic({}) == ResticCli(
                Path("restic.exe"), {"RESTIC_PROGRESS_FPS": "0.016667"}
            )

    def test_verbose(self):
        """A supplied verbosity level should be should be included in the returned class instance"""
        assert app.get_restic({}, verbose=2).verbose == 2

    def test_path(self):
        """A supplied restic path should be included in the returned class instance"""
        config = {"path": "/usr/local/bin/restic"}
        assert app.get_restic(config).path == Path("/usr/local/bin/restic")

    def test_progress_fps(self):
        """A supplied value for RESTIC_PROGRESS_FPS should be included in the returned class instance"""
        config = {"environment": {"RESTIC_PROGRESS_FPS": "0.003333"}}
        assert app.get_restic(config).environment_vars == {
            "RESTIC_PROGRESS_FPS": "0.003333"
        }


class TestGetPolicy:
    """Tests for the function app.get_policy"""

    def test_no_policy(self):
        """an empty dictionary (i.e. the user set no policy options) should return None"""
        assert app.get_policy({}) is None

    @pytest.mark.parametrize(
        "policy, expectation",
        [
            ({"keep-last": 10}, Policy(10, 0, 0, 0, 0)),
            ({"keep-daily": 10}, Policy(0, 10, 0, 0, 0)),
            ({"keep-weekly": 10}, Policy(0, 0, 10, 0, 0)),
            ({"keep-monthly": 10}, Policy(0, 0, 0, 10, 0)),
            ({"keep-yearly": 10}, Policy(0, 0, 0, 0, 10)),
        ],
    )
    def test_policy_options(self, policy, expectation):
        """one or more policy options should return a Policy instance, with any unset options set to 0 (disabled)"""
        assert app.get_policy(policy) == expectation

    def test_all_policy_options(self):
        """all policy options should be able to be set at once"""
        assert app.get_policy(
            {
                "keep-last": 10,
                "keep-daily": 9,
                "keep-weekly": 8,
                "keep-monthly": 7,
                "keep-yearly": 6,
            }
        ) == Policy(10, 9, 8, 7, 6)

    def test_non_integer_input(self):
        """an invalid policy input (i.e. not-an-integer, or a negative integer) should raise a RuntimeError"""
        with pytest.raises(RuntimeError):
            app.get_policy({"keep-last": "foo"})

    def test_invalid_policy(self):
        """inputs that would lead to an invalid policy (i.e. all zeroes) should raise a RuntimeError"""
        with pytest.raises(RuntimeError):
            app.get_policy({"keep-last": 0})

    @pytest.mark.parametrize(
        "state",
        [True, False],
    )
    def test_no_current_set(self, state):
        """setting exclude-current-period should set no_current in the returned Policy instance"""
        assert app.get_policy(
            {"keep-last": 1, "exclude-current-period": state}
        ) == Policy(1, no_current=state)

    def test_no_current_unset(self):
        """omitting exclude-current-period should set no_current to False in the returned Policy instance"""
        assert app.get_policy({"keep-last": 1}) == Policy(1, no_current=False)


class TestGetGroupBy:
    """Tests for the function app.get_group_by"""

    def test_no_grouping(self):
        """an empty dictionary (i.e. the user set no options) should return the default of host/path"""
        assert app.get_group_by({}) == SnapshotGroupByOptions()

    def test_disabled_grouping(self):
        """If user disables grouping, None should be returned"""
        assert app.get_group_by({"host": False, "path": False, "tag": False}) is None

    @pytest.mark.parametrize(
        "options, expectation",
        [
            ({"host": True}, SnapshotGroupByOptions(True, False, False)),
            ({"path": True}, SnapshotGroupByOptions(False, True, False)),
            ({"tag": True}, SnapshotGroupByOptions(False, False, True)),
        ],
    )
    def test_enabled_grouping(self, options, expectation):
        """valid grouping options should be able to be set"""
        assert app.get_group_by(options) == expectation

    @pytest.mark.parametrize(
        "options",
        [
            ({"host": "true"}),
            ({"path": 9}),
            ({"tag": 3.2}),
            ({"host": None}),
            ({"host": 0}),
            ({"host": []}),
        ],
    )
    def test_non_bool_input(self, options):
        """an input that is not a bool, should cause an exception"""
        with pytest.raises(TypeError):
            app.get_group_by(options)


class TestGetRepository:
    """Tests for the function app.get_repository"""

    @pytest.mark.usefixtures("restic_cli_fixture")
    def test_password(self, restic_cli_fixture):
        """A supplied password should be included in the instanced repository"""
        config = {"repository_uri": "/tmp/restic-repo", "password": "secret"}
        assert app.get_repository("myrepo", config, restic_cli_fixture) == Repository(
            "/tmp/restic-repo", "myrepo", restic_cli_fixture, password="secret"
        )

    @pytest.mark.usefixtures("restic_cli_fixture")
    def test_password_file(self, restic_cli_fixture):
        """A supplied password_file should be included in the instanced repository"""
        config = {
            "repository_uri": "/tmp/restic-repo",
            "password_file": "/path/to/secret",
        }
        assert app.get_repository("myrepo", config, restic_cli_fixture) == Repository(
            "/tmp/restic-repo",
            "myrepo",
            restic_cli_fixture,
            password_file="/path/to/secret",
        )

    @pytest.mark.usefixtures("restic_cli_fixture")
    def test_password_command(self, restic_cli_fixture):
        """A supplied password_command should be included in the instanced repository"""
        config = {
            "repository_uri": "/tmp/restic-repo",
            "password_command": "/bin/getsecret myrepo",
        }
        assert app.get_repository("myrepo", config, restic_cli_fixture) == Repository(
            "/tmp/restic-repo",
            "myrepo",
            restic_cli_fixture,
            password_command="/bin/getsecret myrepo",
        )

    @pytest.mark.usefixtures("restic_cli_fixture")
    def test_environment_variables(self, restic_cli_fixture):
        """Any supplied environment variables should be included in the instanced repository"""
        config = {
            "repository_uri": "/tmp/restic-repo",
            "password": "secret",
            "environment": {"RESTIC_COMPRESSION": "true"},
        }
        assert app.get_repository("myrepo", config, restic_cli_fixture) == Repository(
            "/tmp/restic-repo",
            "myrepo",
            restic_cli_fixture,
            password="secret",
            environment_vars={"RESTIC_COMPRESSION": "true"},
        )


class TestCheckRepositoryAccess:
    """Tests for the function app.check_repository_access"""

    @pytest.mark.usefixtures("repository_fixture")
    def test_valid_repository(self, repository_fixture):
        """Should return True in the event of successful access check"""
        with mock.patch.object(
            repository_fixture, "snapshots", return_value=CompletedProcess(["./foo"], 0)
        ):
            assert app.check_repository_access(repository_fixture)

    @pytest.mark.usefixtures("repository_fixture")
    def test_invalid_repository(self, repository_fixture, caplog):
        """Should raise a RuntimeError if the repository is unable to be accessed"""
        with mock.patch.object(
            repository_fixture,
            "snapshots",
            side_effect=CalledProcessError(
                1,
                "notalrealcommand",
                "",
                "this command does not exist\nuse another command\n",
            ),
        ):
            with pytest.raises(RuntimeError):
                app.check_repository_access(repository_fixture)
            assert caplog.messages[0:2] == [
                "this command does not exist",
                "use another command",
            ]

    @pytest.mark.usefixtures("repository_fixture")
    def test_restic_error(self, repository_fixture):
        """Should raise a RuntimeError if the OS throws an exception accessing restic"""
        with mock.patch.object(
            repository_fixture,
            "snapshots",
            side_effect=FileNotFoundError(
                "[Errno 2] No such file or directory: '/usr/local/bin/restic'"
            ),
        ):
            with pytest.raises(RuntimeError):
                app.check_repository_access(repository_fixture)


class TestGetSnapshots:
    """Tests for the function app.get_snapshots"""

    def test_standard_options(self, repository_fixture):
        # mock CompletedProcess
        mock_result = mock.Mock()
        mock_result.stdout = "[]"
        repository_fixture.snapshots = mock.MagicMock(return_value=mock_result)
        # call function
        app.get_snapshots(repository_fixture)
        # check that function was called with expected options
        repository_fixture.snapshots.assert_called_once_with(
            json=True, group_by=None, snap_filter=None
        )

    def test_group_by(self, repository_fixture):
        test_group_by = SnapshotGroupByOptions()
        # mock CompletedProcess
        mock_result = mock.Mock()
        mock_result.stdout = "[]"
        repository_fixture.snapshots = mock.MagicMock(return_value=mock_result)
        # call function
        app.get_snapshots(repository_fixture, group_by=test_group_by)
        # check that function was called with expected options
        repository_fixture.snapshots.assert_called_once_with(
            json=True, group_by=test_group_by, snap_filter=None
        )

    def test_snap_filter(self, repository_fixture):
        test_snap_filter = SnapshotFilterOptions()
        # mock CompletedProcess
        mock_result = mock.Mock()
        mock_result.stdout = "[]"
        repository_fixture.snapshots = mock.MagicMock(return_value=mock_result)
        # call function
        app.get_snapshots(repository_fixture, snap_filter=test_snap_filter)
        # check that function was called with expected options
        repository_fixture.snapshots.assert_called_once_with(
            json=True, group_by=None, snap_filter=test_snap_filter
        )


class TestApplyPolicy:
    """Tests for the function app.apply_policy"""

    @pytest.mark.usefixtures("snapshot_list_fixture")
    def test_policy_applied_to_all_groups(self, snapshot_list_fixture):
        """policy should be applied to all snapshot groups within a snapshot list"""
        test_policy = Policy(1)  # keep only one snapshot
        filtered_list = app.apply_policy(snapshot_list_fixture, test_policy)
        # check all groups have only one snapshot
        for group in filtered_list.snapshot_groups:
            assert len(group.snapshots) == 1

    @pytest.mark.usefixtures("snapshot_list_fixture")
    def test_empty_group_not_returned(self, snapshot_list_fixture):
        """
        if a group has all snapshots filtered by a policy, it should not be present
        in the returned snapshot list
        """
        # set a policy that will return nothing
        test_policy = Policy(1)
        # set "last" to zero after init, to avoid triggering "all zeroes not allowed" check
        test_policy.last = 0
        filtered_list = app.apply_policy(snapshot_list_fixture, test_policy)
        # check no groups were returned
        assert len(filtered_list.snapshot_groups) == 0


class TestCopySnapshots:
    """Tests for the function app.copy_snapshots"""

    def return_kwargs(self, *args, **kwargs):
        """function that returns all kwargs passed to it"""
        return kwargs

    @pytest.mark.usefixtures(
        "snapshot_list_fixture", "repository_fixture", "restic_cli_fixture"
    )
    def test_copy_success(
        self, snapshot_list_fixture, repository_fixture, restic_cli_fixture, monkeypatch
    ):
        """Should return true if the copy operation is successful"""
        monkeypatch.setattr(
            "restic_replica.app.get_snapshots",
            lambda *args, **kwargs: snapshot_list_fixture,
        )
        with mock.patch.object(
            repository_fixture, "copy", return_value=CompletedProcess(["./foo"], 0)
        ):
            assert isinstance(
                app.copy_snapshots(
                    Repository(
                        "/tmp/restic-repo2",
                        "myrepo2",
                        restic_cli_fixture,
                        password="secret2",
                    ),
                    repository_fixture,
                ),
                CompletedProcess,
            )

    @pytest.mark.usefixtures(
        "snapshot_list_fixture", "repository_fixture", "restic_cli_fixture"
    )
    def test_copy_fail(
        self,
        snapshot_list_fixture,
        repository_fixture,
        restic_cli_fixture,
        caplog,
        monkeypatch,
    ):
        """Should raise RuntimeError if the copy operation fails"""
        monkeypatch.setattr(
            "restic_replica.app.get_snapshots",
            lambda *args, **kwargs: snapshot_list_fixture,
        )
        with mock.patch.object(
            repository_fixture,
            "copy",
            side_effect=CalledProcessError(
                1,
                "notalrealcommand",
                "",
                "this command does not exist\nuse another command\n",
            ),
        ):
            with pytest.raises(RuntimeError):
                app.copy_snapshots(
                    Repository(
                        "/tmp/restic-repo2",
                        "myrepo2",
                        restic_cli_fixture,
                        password="secret2",
                    ),
                    repository_fixture,
                )
            assert caplog.messages[0:2] == [
                "this command does not exist",
                "use another command",
            ]

    @pytest.mark.usefixtures("repository_fixture", "restic_cli_fixture")
    def test_restic_error(self, repository_fixture, restic_cli_fixture):
        """Should raise a RuntimeError if the OS throws an exception accessing restic"""
        with mock.patch.object(
            repository_fixture,
            "copy",
            side_effect=FileNotFoundError(
                "[Errno 2] No such file or directory: '/usr/local/bin/restic'"
            ),
        ):
            with pytest.raises(RuntimeError):
                app.copy_snapshots(
                    Repository(
                        "/tmp/restic-repo2",
                        "myrepo2",
                        restic_cli_fixture,
                        password="secret2",
                    ),
                    repository_fixture,
                )

    @pytest.mark.usefixtures(
        "repository_fixture",
        "restic_cli_fixture",
        "snapshot_list_fixture",
    )
    def test_snapshot_list(
        self, repository_fixture, restic_cli_fixture, snapshot_list_fixture
    ):
        """A SnapshotList object should be passed if a policy is provided"""
        with mock.patch.object(repository_fixture, "copy", self.return_kwargs):
            with mock.patch(
                "restic_replica.app.get_snapshots",
                return_value=snapshot_list_fixture,
            ):
                result = app.copy_snapshots(
                    Repository(
                        "/tmp/restic-repo2",
                        "myrepo2",
                        restic_cli_fixture,
                        password="secret2",
                    ),
                    repository_fixture,
                    policy=Policy(99999),
                )
                assert isinstance(result["snapshots"], SnapshotList)

    @pytest.mark.usefixtures(
        "snapshot_list_fixture", "repository_fixture", "restic_cli_fixture"
    )
    def test_no_snapshot_list(
        self, snapshot_list_fixture, repository_fixture, restic_cli_fixture, monkeypatch
    ):
        """A SnapshotList object should not be passed if a policy is not provided"""
        monkeypatch.setattr(
            "restic_replica.app.get_snapshots",
            lambda *args, **kwargs: snapshot_list_fixture,
        )
        with mock.patch.object(repository_fixture, "copy", self.return_kwargs):
            result = app.copy_snapshots(
                Repository(
                    "/tmp/restic-repo2",
                    "myrepo2",
                    restic_cli_fixture,
                    password="secret2",
                ),
                repository_fixture,
            )
            assert result["snapshots"] is None

    @pytest.mark.usefixtures(
        "snapshot_list_fixture", "repository_fixture", "restic_cli_fixture"
    )
    def test_dry_run(
        self, snapshot_list_fixture, repository_fixture, restic_cli_fixture, monkeypatch
    ):
        """if the dry_run argument is passed, systemexit should be raised, and copy should not be called"""
        monkeypatch.setattr(
            "restic_replica.app.get_snapshots",
            lambda *args, **kwargs: snapshot_list_fixture,
        )
        # raise RuntimeError if copy is called
        with mock.patch.object(repository_fixture, "copy", side_effect=RuntimeError):
            # assert SystemExit is raised, not RuntimeError
            with pytest.raises(SystemExit):
                app.copy_snapshots(
                    Repository(
                        "/tmp/restic-repo2",
                        "myrepo2",
                        restic_cli_fixture,
                        password="secret2",
                    ),
                    repository_fixture,
                    dry_run=True,
                )

    @pytest.mark.usefixtures("repository_fixture", "restic_cli_fixture")
    def test_empty_source_repository(
        self, repository_fixture, restic_cli_fixture, monkeypatch
    ):
        """an empty source repository should raise a RuntimeError"""
        monkeypatch.setattr(
            "restic_replica.app.get_snapshots", lambda *args, **kwargs: SnapshotList([])
        )
        with pytest.raises(RuntimeError):
            app.copy_snapshots(
                Repository(
                    "/tmp/restic-repo2",
                    "myrepo2",
                    restic_cli_fixture,
                    password="secret2",
                ),
                repository_fixture,
                dry_run=True,
            )

    @pytest.mark.usefixtures(
        "snapshot_list_fixture", "repository_fixture", "restic_cli_fixture"
    )
    def test_empty_after_policy_applied(
        self, snapshot_list_fixture, repository_fixture, restic_cli_fixture, monkeypatch
    ):
        """no snapshots remaining after policy is applied should raise a RuntimeError"""
        monkeypatch.setattr(
            "restic_replica.app.get_snapshots",
            lambda *args, **kwargs: snapshot_list_fixture,
        )
        # set a policy that will return nothing
        test_policy = Policy(1)
        # set "last" to zero after init, to avoid triggering "all zeroes not allowed" check
        test_policy.last = 0
        with pytest.raises(RuntimeError):
            app.copy_snapshots(
                Repository(
                    "/tmp/restic-repo2",
                    "myrepo2",
                    restic_cli_fixture,
                    password="secret2",
                ),
                repository_fixture,
                policy=test_policy,
            )
