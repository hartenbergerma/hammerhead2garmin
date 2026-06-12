import logging
from pathlib import Path

from garminconnect import Garmin, GarminConnectConnectionError

logger = logging.getLogger(__name__)

_DUPLICATE_MARKER = "already exists (duplicate)"


class GarminClient:
    def __init__(self, username: str, password: str):
        self._client = Garmin(username, password)

    def login(self) -> None:
        self._client.login()

    def import_fit(self, filepath: Path) -> bool:
        """Upload a FIT file as an import.

        Uses import_activity() instead of upload_activity() so Garmin does not
        re-export the activity to connected third parties (e.g. Strava).

        Returns True on success, False if Garmin reports a duplicate (409).
        """
        try:
            self._client.import_activity(str(filepath))
            return True
        except GarminConnectConnectionError as exc:
            if _DUPLICATE_MARKER in str(exc):
                logger.info("Activity already exists in Garmin, skipping: %s", filepath.stem)
                return False
            raise
