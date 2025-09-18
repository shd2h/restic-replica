from pathlib import Path
import pytest
from subprocess import CalledProcessError, CompletedProcess
import textwrap
import tomllib
from unittest import mock

from restic_replica import app
from restic_replica.repository import Repository, ResticCli


class TestEnsureConfigFile:
    """Tests for the function app.ensure_config_file"""

    def test_existing_config_file(self, tmp_path):
        assert app.ensure_config_file(tmp_path) == tmp_path

    @mock.patch("pathlib.Path.exists", return_value=True)
    @mock.patch("platform.system", return_value="Linux")
    def test_default_config_file_path_nonwin(self, *args):
        assert app.ensure_config_file() == Path.home() / ".restic-replica/config.toml"

    @mock.patch("pathlib.Path.exists", return_value=True)
    @mock.patch("platform.system", return_value="Windows")
    def test_default_config_file_path_win(self, *args):
        assert (
            app.ensure_config_file()
            == Path.home() / "AppData/Local/restic-replica/config.toml"
        )

    @mock.patch("pathlib.Path.mkdir", return_value=None)
    @mock.patch("shutil.copyfile", return_value=None)
    def test_missing_config_file(self, *args):
        with pytest.raises(SystemExit):
            app.ensure_config_file(Path("/not/a/real/path"))


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
            assert app.get_logdir({}) == Path.home() / "AppData/Local/.restic-replica"


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

    @pytest.mark.usefixtures("repository_fixture", "restic_cli_fixture")
    def test_copy_success(self, repository_fixture, restic_cli_fixture):
        """Should return true if the copy operation is successful"""
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

    @pytest.mark.usefixtures("repository_fixture", "restic_cli_fixture")
    def test_copy_fail(self, repository_fixture, restic_cli_fixture):
        """Should raise RuntimeError if the copy operation fails"""
        with mock.patch.object(
            repository_fixture,
            "copy",
            side_effect=CalledProcessError(1, "notalrealcommand"),
        ):
            with pytest.raises(RuntimeError):
                app.copy_snapshots(
                    repository_fixture,
                    Repository(
                        "/tmp/restic-repo2",
                        "myrepo2",
                        restic_cli_fixture,
                        password="secret2",
                    ),
                )
