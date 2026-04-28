from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


class DiskCache:
    def __init__(self, root: Path, ttl_seconds: int = 3600) -> None:
        self.root = root
        self.ttl = timedelta(seconds=ttl_seconds)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, namespace: str, key: str) -> Path:
        digest = hashlib.sha256(f"{namespace}:{key}".encode()).hexdigest()
        return self.root / f"{digest}.json"

    def get(self, namespace: str, key: str) -> dict[str, Any] | None:
        path = self._path(namespace, key)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            return None
        expires = datetime.fromisoformat(data["expires_at"])
        if datetime.now(UTC) > expires:
            path.unlink(missing_ok=True)
            return None
        payload = data.get("payload")
        if isinstance(payload, dict):
            return payload
        return None

    def set(self, namespace: str, key: str, payload: dict[str, Any]) -> None:
        path = self._path(namespace, key)
        data = {
            "expires_at": (datetime.now(UTC) + self.ttl).isoformat(),
            "payload": payload,
        }
        path.write_text(json.dumps(data))
