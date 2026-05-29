from messoyakha_coupling.settings.storages.s3 import IcebergSettingsBase
from messoyakha_finam_sdk.enums.intervals import FinamIntervalEnum
from messoyakha_finam_sdk.enums.markets import FinamMarketEnum


class TestStrategySettings(IcebergSettingsBase):
    NAMESPACE: str = "dlh"

    BUCKET: str = "f8e90488-f511555d-274b-4258-bffc-572dd1900382"

    ACCESS_KEY: str
    SECRET_KEY: str

    TICKER: str = "SIBN"
    MARKET: str = FinamMarketEnum.MISX.value
    INTERVAL: str = FinamIntervalEnum.ONE_DAY.value
