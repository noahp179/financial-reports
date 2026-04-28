from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_path: Path = Path("config/report_config.yaml")
    logging_config_path: Path = Path("config/logging.yaml")
    output_dir: Path = Path("out")
    raw: dict[str, Any] = Field(default_factory=dict)


def load_settings(config_path: str | Path) -> Settings:
    path = Path(config_path)
    raw = yaml.safe_load(path.read_text())
    return Settings(config_path=path, raw=raw)
