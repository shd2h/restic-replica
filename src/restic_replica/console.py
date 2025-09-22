import argparse
from datetime import datetime
import logging
from pathlib import Path
from typing import Optional

from restic_replica import __version__

logger = logging.getLogger(__name__)


class InfoOnly(logging.Filter):
    """Return only messages of level logging.INFO"""

    def filter(self, record):
        return record.levelno == logging.INFO


class NoInfo(logging.Filter):
    """Return all messages except those with level logging.INFO"""

    def filter(self, record):
        return record.levelno != logging.INFO


def parse_cli_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """
    Process arguments provided via cli

    Returns:
        args: Simple object used for storing key/value attribute pairs
    """
    about = "Copy snapshots from one restic repository to another"
    parser = argparse.ArgumentParser(prog="restic-replica", description=about)
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="make restic output more verbose (specify multiple times, max level/times is 2)",
        action="count",
        default=0,
    )
    return parser.parse_args(argv)


def setup_logging(
    logger: logging.Logger = logging.getLogger("restic_replica"),
    logdir: Optional[Path] = None,
    debug: bool = False,
) -> logging.Logger:

    # set debugging log level if specified
    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # console handling is split into two, so the levelname is not prepended to info messages, for aesthetic reasons.
    # setup logging to console for all messages _except_ info (i.e. debug, warn, error, fatal)
    ch = logging.StreamHandler()
    ch.addFilter(NoInfo())
    ch.setFormatter(logging.Formatter(fmt="%(levelname)s: %(message)s"))
    logger.addHandler(ch)
    # setup logging to console for info messages
    ch_info = logging.StreamHandler()
    ch_info.addFilter(InfoOnly())
    logger.addHandler(ch_info)

    # setup logging to file
    if logdir:
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        logname = f"restic-replica_{timestamp}.log"
        # create logging dir
        logdir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(logdir / f"{logname}")
        fh_formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S%z",
        )
        fh.setFormatter(fh_formatter)
        logger.addHandler(fh)

    # return the logger object
    return logger


def logging_headers(version: str) -> None:
    logger.info("==============================")
    logger.info(f"  restic-replica {version}")
    logger.info("==============================")
    logger.info(f"Program start @ {datetime.now().strftime("%Y/%m/%d %H:%M:%S%z")}")
