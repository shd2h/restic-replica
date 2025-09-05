import pytest
from subprocess import CalledProcessError
import textwrap
import tomllib
from unittest import mock

from restic_replica import app
from restic_replica.repository import Repository


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


class TestGetRepository:
    """Tests for the function app.get_repository"""

    def test_password(self):
        """A supplied password should be included in the instanced repository"""
        config = {"repository_uri": "/tmp/restic-repo", "password": "secret"}
        assert app.get_repository("myrepo", config) == Repository(
            "/tmp/restic-repo", "myrepo", password="secret"
        )

    def test_password_file(self):
        """A supplied password_file should be included in the instanced repository"""
        config = {
            "repository_uri": "/tmp/restic-repo",
            "password_file": "/path/to/secret",
        }
        assert app.get_repository("myrepo", config) == Repository(
            "/tmp/restic-repo", "myrepo", password_file="/path/to/secret"
        )

    def test_password_command(self):
        """A supplied password_command should be included in the instanced repository"""
        config = {
            "repository_uri": "/tmp/restic-repo",
            "password_command": "/bin/getsecret myrepo",
        }
        assert app.get_repository("myrepo", config) == Repository(
            "/tmp/restic-repo", "myrepo", password_command="/bin/getsecret myrepo"
        )

    def test_environment_variables(self):
        """Any supplied environment variables should be included in the instanced repository"""
        config = {
            "repository_uri": "/tmp/restic-repo",
            "password": "secret",
            "environment": {"RESTIC_COMPRESSION": "true"},
        }
        assert app.get_repository("myrepo", config) == Repository(
            "/tmp/restic-repo",
            "myrepo",
            password="secret",
            environment_vars={"RESTIC_COMPRESSION": "true"},
        )


class TestCheckRepositoryAccess:
    """Tests for the function app.check_repository_access"""

    @pytest.mark.usefixtures("repository_fixture")
    def test_valid_repository(self, repository_fixture):
        """Should return True in the event of successful access check"""
        with mock.patch.object(repository_fixture, "snapshots", return_value=True):
            assert app.check_repository_access(repository_fixture)

    @pytest.mark.usefixtures("repository_fixture")
    def test_invalid_repository(self, repository_fixture):
        """Should raise a RuntimeError if the repository is unable to be accessed"""
        with mock.patch.object(
            repository_fixture,
            "snapshots",
            side_effect=CalledProcessError(1, "notalrealcommand"),
        ):
            with pytest.raises(RuntimeError):
                app.check_repository_access(repository_fixture)


class TestCopySnapshots:
    """Tests for the function app.copy_snapshots"""

    @pytest.mark.usefixtures("repository_fixture")
    def test_copy_success(self, repository_fixture):
        """Should return true if the copy operation is successful"""
        with mock.patch.object(repository_fixture, "copy", return_value=True):
            assert app.copy_snapshots(
                Repository("/tmp/restic-repo2", "myrepo2", password="secret2"),
                repository_fixture,
            )

    @pytest.mark.usefixtures("repository_fixture")
    def test_copy_fail(self, repository_fixture):
        """Should raise RuntimeError if the copy operation fails"""
        with mock.patch.object(
            repository_fixture,
            "copy",
            side_effect=CalledProcessError(1, "notalrealcommand"),
        ):
            with pytest.raises(RuntimeError):
                app.copy_snapshots(
                    repository_fixture,
                    Repository("/tmp/restic-repo2", "myrepo2", password="secret2"),
                )
