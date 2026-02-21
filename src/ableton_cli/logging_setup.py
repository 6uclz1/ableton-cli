from __future__ import annotations

import logging
import sys
from pathlib import Path


def configure_logging(verbose: bool, quiet: bool, log_file: str | None) -> None:
    logger = logging.getLogger("ableton_cli")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if quiet:
        stream_level = logging.ERROR
    elif verbose:
        stream_level = logging.DEBUG
    else:
        stream_level = logging.INFO

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setLevel(stream_level)
    stream_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(stream_handler)

    if log_file:
        file_handler = logging.FileHandler(Path(log_file), encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        )
        logger.addHandler(file_handler)
