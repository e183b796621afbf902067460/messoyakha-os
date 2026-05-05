from pep_sdk.settings._common.iceberg import IcebergSettingsBase
from pep_sdk.settings._common.s3 import S3SettingsBase


class SettingsBase(IcebergSettingsBase, S3SettingsBase): ...
