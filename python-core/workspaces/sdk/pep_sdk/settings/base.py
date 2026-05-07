from datetime import datetime, timezone

from pep_sdk.settings._common.s3 import IcebergSettingsBase


class SettingsBase(IcebergSettingsBase):
    TRIGGER_DATE: datetime = datetime.now(tz=timezone.utc)
