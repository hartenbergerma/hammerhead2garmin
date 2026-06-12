import json
from datetime import datetime, timezone
from pathlib import Path


class State:
    def __init__(self, path: Path):
        self._path = path
        self._data: dict = {"last_sync_at": None, "synced": {}}
        if path.exists():
            self._data = json.loads(path.read_text())

    def is_synced(self, activity_id: str) -> bool:
        return str(activity_id) in self._data["synced"]

    def mark_synced(self, activity_id: str) -> None:
        self._data["synced"][str(activity_id)] = datetime.now(timezone.utc).isoformat()

    def get_last_sync(self) -> datetime | None:
        raw = self._data.get("last_sync_at")
        if raw is None:
            return None
        return datetime.fromisoformat(raw)

    def set_last_sync(self, dt: datetime) -> None:
        self._data["last_sync_at"] = dt.isoformat()

    def save(self) -> None:
        self._path.write_text(json.dumps(self._data, indent=2))
