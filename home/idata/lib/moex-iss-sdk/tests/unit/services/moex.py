from datetime import datetime, timezone

import pytest
from loguru import logger
from polars import Config, DataFrame

from messoyakha_moex_iss_sdk.schemas.history_security import MOEXSpotHistorySecurityInputSchema
from messoyakha_moex_iss_sdk.services.moex import MOEXStockIndexService


Config.set_tbl_cols(-1)
Config.set_fmt_str_lengths(1024)


class TestMOEXStockIndexService:
    @pytest.mark.asyncio
    async def test_get_ohlcv(self) -> None:
        moex: MOEXStockIndexService = MOEXStockIndexService()
        data: DataFrame = await moex.get_ohlcv(
            input_schema=MOEXSpotHistorySecurityInputSchema(
                ticker="IMOEX",
                currency="RUB",
                start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
                end_time=datetime(2026, 2, 20, tzinfo=timezone.utc),
            )
        )
        logger.info(data.head())
        logger.info(f"Got OHLCV: {data.shape}.")

        assert isinstance(data, DataFrame)
        assert not data.is_empty()
