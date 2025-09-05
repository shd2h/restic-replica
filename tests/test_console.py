from datetime import datetime
import logging
import pytest
from unittest import mock
from pathlib import Path

from restic_replica import console


class TestSetupLogging:
    """Tests for the function console.setup_logging"""

    def test_default_logdir(self):
        """If no logdir specified, default logdir should be set"""
        logger = console.setup_logging()
        assert (
            Path(logger.handlers[1].baseFilename).parent
            == Path.home() / ".restic-replica"
        )

    def test_custom_logdir(self, tmp_path):
        """Custom logdir should be set correctly"""
        logger = console.setup_logging(logdir=tmp_path)
        assert Path(logger.handlers[1].baseFilename).parent == tmp_path

    def test_no_logfile(self):
        """Logdir set to None should result in no logfile handler"""
        logger = console.setup_logging(logdir=None)
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.StreamHandler)

    def test_logname(self, tmp_path):
        """Log name should be made up of program name and iso timestamp"""
        logger = console.setup_logging(logdir=tmp_path)
        logname = Path(logger.handlers[1].baseFilename).stem
        logname_parts = logname.split("_")
        assert logname_parts[0] == "restic-replica"
        assert datetime.fromisoformat(logname_parts[1]) is not None

    @pytest.mark.parametrize("debug", [True, False])
    def test_debug(self, tmp_path, debug):
        """Setting debug boolen should change the logger level"""
        logger = console.setup_logging(logdir=tmp_path, debug=debug)
        assert logger.getEffectiveLevel() == logging.DEBUG if debug else logging.INFO

    def test_logdir_error(self, tmp_path):
        """Inaccessible log directory should raise an OSError"""
        with mock.patch("pathlib.Path.mkdir", side_effect=PermissionError):
            with pytest.raises(OSError):
                console.setup_logging(logdir=tmp_path)


class TestLoggingHeaders:
    """Tests for the function console.logging_headers"""

    def test_logging_headers(self, caplog):
        """Logging headers should be emitted"""
        caplog.set_level(logging.INFO)
        console.logging_headers("9.9.9")
        ts = (
            caplog.messages[3].split("@")[1].strip()
        )  # extract timestamp from the 4th line
        assert caplog.messages == [
            "==============================",
            "  restic-replica 9.9.9",
            "==============================",
            f"Program start @ {ts}",
        ]
