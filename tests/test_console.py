from datetime import datetime
from logging import StreamHandler
import pytest
from unittest import mock
from pathlib import Path

from restic_replica import console


class TestSetupLogging:
    """Tests for the function console.setup_logging"""

    def test_default_logdir(self):
        logger = console.setup_logging()
        assert (
            Path(logger.handlers[1].baseFilename).parent
            == Path.home() / ".restic-replica"
        )

    def test_custom_logdir(self, tmp_path):
        logger = console.setup_logging(logdir=tmp_path)
        assert Path(logger.handlers[1].baseFilename).parent == tmp_path

    def test_no_logfile(self):
        logger = console.setup_logging(logdir=None)
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], StreamHandler)

    def test_logname(self, tmp_path):
        logger = console.setup_logging(logdir=tmp_path)
        logname = Path(logger.handlers[1].baseFilename).stem
        logname_parts = logname.split("_")
        assert logname_parts[0] == "restic-replica"
        assert datetime.fromisoformat(logname_parts[1]) is not None

    @pytest.mark.parametrize("debug", [True, False])
    def test_debug(self, tmp_path, debug):
        logger = console.setup_logging(logdir=tmp_path, debug=debug)
        assert logger.getEffectiveLevel() == 10 if debug else 20

    def test_logdir_error(self, tmp_path):
        with mock.patch("pathlib.Path.mkdir", side_effect=PermissionError):
            with pytest.raises(OSError):
                console.setup_logging(logdir=tmp_path)
