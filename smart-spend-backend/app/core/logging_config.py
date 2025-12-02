"""Central logging configuration for Smart Spend."""

import logging


def configure_logging():
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt)


def get_logger(name: str = "smart_spend"):
    configure_logging()
    return logging.getLogger(name)
