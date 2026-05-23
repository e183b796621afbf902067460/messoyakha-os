from datetime import datetime, timezone

from messoyakha_coupling.settings.storages.s3 import IcebergSettingsBase


class DLHSettings(IcebergSettingsBase):
    NAMESPACE: str = "dlh"

    BUCKET: str = "f8e90488-f511555d-274b-4258-bffc-572dd1900382"

    ACCESS_KEY: str
    SECRET_KEY: str

    TRIGGER_DATE: datetime = datetime.now(tz=timezone.utc)
