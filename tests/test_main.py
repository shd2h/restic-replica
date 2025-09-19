from importlib import metadata
import logging
from packaging import version
from pathlib import Path
import pytest
from subprocess import CompletedProcess
from unittest import mock

from restic_replica import __version__, __main__


def test_version():
    """The application version in pyproject.toml must match the application version in restic_replica/__init__.py"""
    assert version.parse(__version__) == version.parse(
        metadata.version("restic-replica")
    )


class TestMain:
    """Tests for the function __main__.main"""

    @pytest.fixture(autouse=True)
    def mock_ensure_config_file(self, monkeypatch):
        monkeypatch.setattr(
            "restic_replica.app.ensure_config_file", lambda *args, **kwargs: Path()
        )

    @pytest.fixture(autouse=True)
    def mock_read_config_file(self, monkeypatch):
        monkeypatch.setattr(
            "restic_replica.app.read_config_file",
            lambda *args, **kwargs: {"restic": {}, "source": {}, "destination": {}},
        )

    @pytest.fixture(autouse=True)
    def mock_get_logdir(self, monkeypatch):
        monkeypatch.setattr(
            "restic_replica.app.get_logdir", lambda *args, **kwargs: None
        )

    @pytest.fixture(autouse=True)
    def mock_setup_logging(self, monkeypatch, logger_fixture):
        monkeypatch.setattr(
            "restic_replica.console.setup_logging",
            lambda *args, **kwargs: logger_fixture,
        )

    @pytest.fixture(autouse=True)
    def mock_logging_headers(self, monkeypatch):
        monkeypatch.setattr(
            "restic_replica.console.logging_headers",
            lambda *args, **kwargs: None,
        )

    @pytest.fixture(autouse=True)
    def mock_get_restic(self, monkeypatch, restic_cli_fixture):
        monkeypatch.setattr(
            "restic_replica.app.get_restic", lambda *args, **kwargs: restic_cli_fixture
        )

    @pytest.fixture(autouse=True)
    def mock_get_repository(self, monkeypatch, repository_fixture):
        monkeypatch.setattr(
            "restic_replica.app.get_repository",
            lambda *args, **kwargs: repository_fixture,
        )

    @pytest.fixture(autouse=True)
    def mock_check_repository_access(self, monkeypatch):
        monkeypatch.setattr(
            "restic_replica.app.check_repository_access",
            lambda *args, **kwargs: True,
        )

    @pytest.fixture(autouse=True)
    def mock_copy_snapshots(self, monkeypatch):
        monkeypatch.setattr(
            "restic_replica.app.copy_snapshots",
            lambda *args, **kwargs: CompletedProcess(
                ["foo"], 0, stdout=b"did something\n"
            ),
        )

    def test_copy_success(self, caplog):
        """A successful copy should log an informational message"""
        caplog.set_level(logging.INFO)
        __main__.main()
        assert caplog.records[3].message == "Finished copying snapshots"

    @mock.patch(
        "restic_replica.app.copy_snapshots",
        return_value=CompletedProcess(
            ["foo"], 0, stdout=None
        ),  # stdout will be None if no snapshots needed to be copied
    )
    def test_no_snapshots(self, mock_func_under_test, caplog):
        """If there are no snapshots to copy, an informational message should be logged"""
        caplog.set_level(logging.INFO)
        __main__.main()
        assert (
            caplog.records[3].message
            == "All snapshots from the source are already present in the destination repository"
        )

    @mock.patch("restic_replica.app.check_repository_access", side_effect=RuntimeError)
    def test_repository_access_failure(self, mock_func_under_test):
        """A repository access failure should raise a SystemExit"""
        with pytest.raises(SystemExit):
            __main__.main()
        # The destination repository should not be checked if the access check on the source fails
        mock_func_under_test.assert_called_once()

    @mock.patch("restic_replica.app.copy_snapshots", side_effect=RuntimeError)
    def test_copy_failure(self, *args):
        """A snapshot copy failure should raise a SystemExit"""
        with pytest.raises(SystemExit):
            __main__.main()
