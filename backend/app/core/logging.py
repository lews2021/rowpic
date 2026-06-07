"""Logging configuration."""
import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    fmt = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
    for name in ("PIL", "urllib3", "rawpy", "libraw"):
        logging.getLogger(name).setLevel(logging.WARNING)
