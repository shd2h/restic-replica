import pytest
import textwrap
import tomllib

from restic_replica import app


class TestReadConfigFile:

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
