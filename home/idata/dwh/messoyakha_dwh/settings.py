from messoyakha_sdk.settings.s3 import S3SettingsBase

from messoyakha_dlh.settings import DLHSettings


class DWHSettings(S3SettingsBase):
    ACCESS_KEY: str
    SECRET_KEY: str

    DLH: DLHSettings
