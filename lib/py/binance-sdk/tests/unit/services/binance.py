import pytest
from loguru import logger
from nautilus_trader.model.currencies import USDT
from polars import Config, DataFrame

from messoyakha_binance_sdk.enums.intervals import BinanceIntervalEnum
from messoyakha_binance_sdk.schemas.klines import BinanceKlinesSpotInputSchema
from messoyakha_binance_sdk.services.binance import BinanceSpotService


Config.set_tbl_cols(-1)
Config.set_fmt_str_lengths(1024)


class TestBinanceSpotService:
    @pytest.mark.asyncio
    async def test_get_ohlcv(self) -> None:
        binance: BinanceSpotService = BinanceSpotService()
        await binance.ping()
        data: DataFrame = await binance.get_ohlcv(
            input_schema=BinanceKlinesSpotInputSchema(
                ticker="BTC",
                interval=BinanceIntervalEnum.ONE_DAY,
                currency=str(USDT),
                start_time="2026-07-01",
                end_time="2026-07-11",
            )
        )
        logger.info(data.head())
        logger.info(f"Got OHLCV: {data.shape}.")

        assert isinstance(data, DataFrame)
        assert not data.is_empty()
