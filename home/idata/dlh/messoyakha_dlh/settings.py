from datetime import datetime, timezone

from messoyakha_sdk.settings.s3 import S3SettingsBase


class DLHSettings(S3SettingsBase):
    ACCESS_KEY: str
    SECRET_KEY: str
    TRIGGER_DATE: datetime = datetime.now(tz=timezone.utc)
