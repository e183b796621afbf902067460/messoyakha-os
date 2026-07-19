from messoyakha_sdk.settings.s3 import S3SettingsBase


class DWHSettings(S3SettingsBase):
    ACCESS_KEY: str
    SECRET_KEY: str
