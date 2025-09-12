from datetime import datetime
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# TODO: write into appdata for windows.
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

    # setup formatting
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%SZ",
    )

    # setup logging to console
    ch = logging.StreamHandler()
    logger.addHandler(ch)

    # setup logging to file
    if logdir:
        timestamp = datetime.now().isoformat(timespec="seconds")
        logname = f"restic-replica_{timestamp}.log"
        # create logging dir
        logdir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler("{0}/{1}".format(logdir, logname))
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    # return the logger object
    return logger


def logging_headers(version: str) -> None:
    logger.info("==============================")
    logger.info(f"  restic-replica {version}")
    logger.info("==============================")
    logger.info(f"Program start @ {datetime.now().strftime("%Y/%m/%d %H:%M:%S%z")}")
