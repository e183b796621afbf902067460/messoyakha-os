from datetime import datetime, timezone

import pytest
from loguru import logger
from polars import Config, DataFrame

from messoyakha_moex_iss_sdk.schemas.history_security import MOEXSpotHistorySecurityInputSchema
from messoyakha_moex_iss_sdk.schemas.history_security_total import MOEXHistorySecurityTotalInputSchema
from messoyakha_moex_iss_sdk.schemas.listed_from import MOEXListedFromInputSchema
from messoyakha_moex_iss_sdk.services.moex import MOEXStockIndexService, MOEXStockSharesService


Config.set_tbl_cols(-1)
Config.set_fmt_str_lengths(1024)
Config.set_fmt_float("full")


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

    @pytest.mark.asyncio
    async def test_get_first_trade_date(self) -> None:
        moex: MOEXStockIndexService = MOEXStockIndexService()
        first_trade_date: datetime = await moex.get_first_trade_date(
            input_schema=MOEXListedFromInputSchema(ticker="IMOEX"),
        )
        logger.info(f"First trade date for IMOEX: {first_trade_date}.")

        assert isinstance(first_trade_date, datetime)


class TestMOEXStockSharesService:
    @pytest.mark.asyncio
    async def test_get_ohlcv(self) -> None:
        moex: MOEXStockSharesService = MOEXStockSharesService()
        data: DataFrame = await moex.get_ohlcv(
            input_schema=MOEXSpotHistorySecurityInputSchema(
                ticker="SBER",
                currency="RUB",
                start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
                end_time=datetime(2026, 2, 20, tzinfo=timezone.utc),
            )
        )
        logger.info(data.head())
        logger.info(f"Got OHLCV: {data.shape}.")

        assert isinstance(data, DataFrame)
        assert not data.is_empty()

    @pytest.mark.asyncio
    async def test_get_first_trade_date(self) -> None:
        moex: MOEXStockSharesService = MOEXStockSharesService()
        first_trade_date: datetime = await moex.get_first_trade_date(
            input_schema=MOEXListedFromInputSchema(ticker="SBER"),
        )
        logger.info(f"First trade date for SBER: {first_trade_date}.")

        assert isinstance(first_trade_date, datetime)

    @pytest.mark.asyncio
    async def test_get_total_supply(self) -> None:
        moex: MOEXStockSharesService = MOEXStockSharesService()
        data: DataFrame = await moex.get_total_supply(
            input_schema=MOEXHistorySecurityTotalInputSchema(
                ticker="SBER",
                currency="RUB",
                start_time=datetime(2015, 1, 1, tzinfo=timezone.utc),
                end_time=datetime(2015, 10, 28, tzinfo=timezone.utc),
            )
        )
        logger.info(data.head())
        logger.info(f"Got total supply: {data.shape}.")

        assert isinstance(data, DataFrame)
        assert not data.is_empty()
