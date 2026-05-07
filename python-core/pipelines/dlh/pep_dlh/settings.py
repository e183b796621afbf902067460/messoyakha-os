from pydantic import AnyUrl

from pep_sdk.settings.base import SettingsBase


class Settings(SettingsBase):
    NAMESPACE: str = "dlh"
    URI_CATALOG_PROPERTY: AnyUrl = AnyUrl("sqlite:///dlh-iceberg-metadata.db")

    BUCKET: str = "f8e90488-f511555d-274b-4258-bffc-572dd1900382"

    ACCESS_KEY: str
    SECRET_KEY: str
