from datetime import datetime
import logging
import pytest
from unittest import mock
from pathlib import Path

from restic_replica import __version__, console


class TestInfoOnly:
    """Tests for the class console.InfoOnly"""

    @pytest.mark.parametrize(
        "log_level, expectation",
        [
            (logging.DEBUG, False),
            (logging.INFO, True),
            (logging.WARNING, False),
            (logging.ERROR, False),
            (logging.CRITICAL, False),
        ],
    )
    def test_filter(self, log_level, expectation):
        """Function filter should return only messages of level logging.INFO"""

        log_record = logging.LogRecord(None, log_level, None, None, None, None, None)
        assert console.InfoOnly.filter(None, log_record) is expectation


class TestNoInfo:
    """Tests for the class console.NoInfo"""

    @pytest.mark.parametrize(
        "log_level, expectation",
        [
            (logging.DEBUG, True),
            (logging.INFO, False),
            (logging.WARNING, True),
            (logging.ERROR, True),
            (logging.CRITICAL, True),
        ],
    )
    def test_filter(self, log_level, expectation):
        """Function filter should return all messages except those with level logging.INFO"""

        log_record = logging.LogRecord(None, log_level, None, None, None, None, None)
        assert console.NoInfo.filter(None, log_record) is expectation


class TestParseCliArgs:
    """Tests for the function console.parse_cli_args"""

    def test_version(self, capsys):
        """Should print the name and version of the package, then exit"""
        with pytest.raises(SystemExit):
            console.parse_cli_args(["--version"])
        captured = capsys.readouterr()
        assert captured.out.strip() == f"restic-replica {__version__}"

    def test_verbose(self):
        """should set verbose boolean"""
        assert console.parse_cli_args([]).verbose == 0
        assert console.parse_cli_args(["-v"]).verbose == 1
        assert console.parse_cli_args(["--verbose"]).verbose == 1


class TestSetupLogging:
    """Tests for the function console.setup_logging"""

    @pytest.mark.usefixtures("logger_fixture")
    def test_handlers(self, logger_fixture, tmp_path):
        """Two StreamHandlers and one FileHandler should be configured"""
        logger = console.setup_logging(logger_fixture, logdir=tmp_path)
        assert len(logger.handlers) == 3
        assert isinstance(logger.handlers[0], logging.StreamHandler)
        assert isinstance(logger.handlers[1], logging.StreamHandler)
        assert isinstance(logger.handlers[2], logging.FileHandler)

    @pytest.mark.usefixtures("logger_fixture")
    def test_custom_logdir(self, logger_fixture, tmp_path):
        """Custom logdir should be set correctly"""
        logger = console.setup_logging(logger_fixture, logdir=tmp_path)
        assert Path(logger.handlers[2].baseFilename).parent == tmp_path

    @pytest.mark.usefixtures("logger_fixture")
    def test_no_logdir(self, logger_fixture):
        """Logdir set to None should result in no logfile handler"""
        logger = console.setup_logging(logger_fixture, logdir=None)
        assert len(logger.handlers) == 2
        assert isinstance(logger.handlers[0], logging.StreamHandler)
        assert isinstance(logger.handlers[1], logging.StreamHandler)

    @pytest.mark.usefixtures("logger_fixture")
    def test_logname(self, logger_fixture, tmp_path):
        """Log name should be made up of program name and iso timestamp"""
        logger = console.setup_logging(logger_fixture, logdir=tmp_path)
        logname = Path(logger.handlers[2].baseFilename).stem
        logname_parts = logname.split("_")
        assert logname_parts[0] == "restic-replica"
        assert datetime.fromisoformat(logname_parts[1]) is not None

    @pytest.mark.usefixtures("logger_fixture")
    @pytest.mark.parametrize("debug", [True, False])
    def test_debug(self, logger_fixture, tmp_path, debug):
        """Setting debug boolen should change the logger level"""
        logger = console.setup_logging(logger_fixture, logdir=tmp_path, debug=debug)
        assert logger.getEffectiveLevel() == logging.DEBUG if debug else logging.INFO

    @pytest.mark.usefixtures("logger_fixture")
    def test_logdir_error(self, logger_fixture, tmp_path):
        """Inaccessible log directory should raise an OSError"""
        with mock.patch("pathlib.Path.mkdir", side_effect=PermissionError):
            with pytest.raises(OSError):
                console.setup_logging(logger_fixture, logdir=tmp_path)


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
