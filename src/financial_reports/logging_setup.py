from __future__ import annotations

import logging.config
from pathlib import Path

import structlog
import yaml


def configure_logging(config_path: str | Path) -> None:
    config = yaml.safe_load(Path(config_path).read_text())
    logging.config.dictConfig(config)
    structlog.configure(processors=[structlog.processors.JSONRenderer()])
