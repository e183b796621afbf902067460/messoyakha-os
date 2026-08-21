from datetime import UTC, datetime

import pytest
from loguru import logger
from polars import Config, DataFrame

from messoyakha_sdk.adapters.venues.xcec import XCEC
from messoyakha_sdk.enums.venues.xcec import XCECProductEnum
from messoyakha_yf_sdk.enums.intervals import YFIntervalEnum
from messoyakha_yf_sdk.schemas.history import YFHistoryInputSchema
from messoyakha_yf_sdk.schemas.history_min_date import YFHistoryMinDateInputSchema
from messoyakha_yf_sdk.services.yf import YFService


Config.set_tbl_cols(-1)
Config.set_fmt_str_lengths(1024)


class TestYFService:
    @pytest.mark.asyncio
    async def test_get_ohlcv(self) -> None:
        yf_service: YFService = YFService()
        data: DataFrame = await yf_service.get_ohlcv(
            input_schema=YFHistoryInputSchema(
                ticker="GC=F",
                interval=YFIntervalEnum.ONE_DAY,
                venue=XCEC,
                product=XCECProductEnum.FUTURES,
                currency="USD",
                start_time=datetime(2026, 1, 1, tzinfo=UTC),
                end_time=datetime(2026, 2, 1, tzinfo=UTC),
            )
        )
        logger.info(data.head())
        logger.info(f"Got OHLCV: {data.shape}.")

        assert isinstance(data, DataFrame)
        assert not data.is_empty()

    @pytest.mark.asyncio
    async def test_get_first_trade_date(self) -> None:
        yf_service: YFService = YFService()
        first_trade_date: datetime = await yf_service.get_first_trade_date(
            input_schema=YFHistoryMinDateInputSchema(ticker="GC=F"),
        )
        logger.info(f"First trade date for GC=F: {first_trade_date}.")

        assert isinstance(first_trade_date, datetime)
