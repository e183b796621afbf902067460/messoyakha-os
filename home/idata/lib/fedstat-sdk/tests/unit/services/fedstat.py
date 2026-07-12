from datetime import datetime, timezone

import pytest
from loguru import logger
from polars import Config, DataFrame

from messoyakha_fedstat_sdk.schemas.inflation_rate import FedstatInflationRateInputSchema
from messoyakha_fedstat_sdk.services.fedstat import FedstatService


Config.set_tbl_cols(-1)
Config.set_fmt_str_lengths(1024)


class TestFedstatService:
    @pytest.mark.asyncio
    async def test_get_inflation_rate(self) -> None:
        fedstat: FedstatService = FedstatService()
        data: DataFrame = await fedstat.get_inflation_rate(
            input_schema=FedstatInflationRateInputSchema(
                start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
        )
        logger.info(data.head())
        logger.info(f"Got inflation rate: {data.shape}.")

        assert isinstance(data, DataFrame)
        assert not data.is_empty()
