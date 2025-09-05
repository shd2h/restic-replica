from datetime import datetime
import logging
from pathlib import Path
import sys
from typing import Optional

logger = logging.getLogger(__name__)


def setup_logging(logdir: Optional[Path] = None) -> None:
    if not logdir:
        logdir = Path.home() / ".restic-replica"
    timestamp = datetime.now().isoformat(timespec="seconds")
    logname = f"restic-replica_{timestamp}.log"
    # create logging dir
    logdir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            # logging.FileHandler("{0}/{1}".format(logdir, logname)),
            logging.StreamHandler(sys.stdout),
        ],
    )


def logging_headers(version: str) -> None:
    logger.info("==============================")
    logger.info(f"  restic-replica {version}")
    logger.info("==============================")
    logger.info(f"Program start @ {datetime.now().strftime("%Y/%m/%d %H:%M:%S%z")}")
