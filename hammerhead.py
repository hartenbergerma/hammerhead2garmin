from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
import logging

import jwt
import requests

logger = logging.getLogger(__name__)

_AUTH_URL = "https://dashboard.hammerhead.io/v1/auth/token"
_API_BASE = "https://api.hammerhead.io"
_DASHBOARD_BASE = "https://dashboard.hammerhead.io"

# Candidate field names for the activity start time, tried in order.
_DATE_FIELDS = ("start_time", "startTime", "date", "created_at", "createdAt", "timestamp")


def _parse_activity_date(activity: dict) -> datetime | None:
    for field in _DATE_FIELDS:
        raw = activity.get(field)
        if raw is None:
            continue
        if isinstance(raw, (int, float)):
            return datetime.fromtimestamp(raw, tz=timezone.utc)
        if isinstance(raw, str):
            try:
                return datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                continue
    return None


class HammerheadClient:
    def __init__(self, client_id: str, client_secret: str, username: str, password: str):
        self._token = self._get_token(client_id, client_secret, username, password)
        self._user_id = self._get_user_id()
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {self._token}"

    def _get_token(self, client_id: str, client_secret: str, username: str, password: str) -> str:
        resp = requests.post(
            _AUTH_URL,
            data={
                "grant_type": "password",
                "client_id": client_id,
                "client_secret": client_secret,
                "username": username,
                "password": password,
            },
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _get_user_id(self) -> str:
        payload = jwt.decode(
            self._token,
            options={"verify_signature": False},
            algorithms=["RS256", "HS256"],
        )
        return payload["sub"]

    def get_activities(self, since: datetime | None = None) -> Iterator[dict]:
        page = 1
        warned_no_date = False

        while True:
            resp = self._session.get(
                f"{_API_BASE}/users/{self._user_id}/activities",
                params={"page": page},
            )
            resp.raise_for_status()
            body = resp.json()
            activities = body.get("data", [])

            for activity in activities:
                if since is None:
                    yield activity
                    continue

                act_date = _parse_activity_date(activity)
                if act_date is None:
                    if not warned_no_date:
                        logger.warning(
                            "Could not find a date field on activity %s (keys: %s) — "
                            "yielding it anyway. Known date fields: %s",
                            activity.get("id"),
                            list(activity.keys()),
                            _DATE_FIELDS,
                        )
                        warned_no_date = True
                    yield activity
                elif act_date >= since:
                    yield activity

            if page >= body.get("totalPages", 1):
                break
            page += 1

    def download_fit(self, activity_id: str, dest: Path) -> None:
        resp = self._session.get(
            f"{_DASHBOARD_BASE}/v1/users/{self._user_id}/activities/{activity_id}/file",
            params={"format": "fit"},
            stream=True,
        )
        resp.raise_for_status()
        dest.write_bytes(resp.content)
