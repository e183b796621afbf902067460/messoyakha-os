from datetime import datetime, timezone

from loguru import logger
from polars import Config, DataFrame

from messoyakha_cbr_sdk.schemas.key_rate import CBRInterestRateInputSchema
from messoyakha_cbr_sdk.services.cbr import CBRService


Config.set_tbl_cols(-1)
Config.set_fmt_str_lengths(1024)


class TestCBRService:
    def test_get_interest_rates(self) -> None:
        cbr: CBRService = CBRService()
        data: DataFrame = cbr.get_interest_rates(
            input_schema=CBRInterestRateInputSchema(
                start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
                end_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
            )
        )
        logger.info(data.head())
        logger.info(f"Got interest rates: {data.shape}.")

        assert isinstance(data, DataFrame)
        assert not data.is_empty()
