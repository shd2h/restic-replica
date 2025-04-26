from datetime import datetime
import logging
from pathlib import Path
import sys

logger = logging.getLogger(__name__)


def setup_logging(logdir: Path) -> None:
    if not logdir:
        logdir = Path("~/.restic-replica/")
    timestamp = datetime.now().isoformat(timespec="seconds")
    logname = f"restic-replica_{timestamp}.log"
    # create logging dir
    logdir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            logging.FileHandler("{0}/{1}".format(logdir, logname)),
            logging.StreamHandler(sys.stdout),
        ],
    )
