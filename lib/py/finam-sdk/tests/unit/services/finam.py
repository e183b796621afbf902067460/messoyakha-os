import pytest
from loguru import logger
from nautilus_trader.model.currencies import RUB
from polars import Config, DataFrame

from messoyakha_finam_sdk.enums.intervals import FinamIntervalEnum
from messoyakha_finam_sdk.schemas.bars import FinamBarsMISXSpotInputSchema
from messoyakha_finam_sdk.schemas.clock import FinamPingInputSchema
from messoyakha_finam_sdk.services.finam import FinamMISXSpotService


Config.set_tbl_cols(-1)
Config.set_fmt_str_lengths(1024)


class TestFinamMISXSpotService:
    @pytest.mark.asyncio
    async def test_get_ohlcv(self, secret: str) -> None:
        finam: FinamMISXSpotService = FinamMISXSpotService()
        await finam.ping(input_schema=FinamPingInputSchema(secret=secret))
        data: DataFrame = await finam.get_ohlcv(
            input_schema=FinamBarsMISXSpotInputSchema(
                secret=secret,
                ticker="SBER",
                interval=FinamIntervalEnum.ONE_DAY,
                currency=str(RUB),
                start_time="2026-01-01",
                end_time="2026-02-20",
            )
        )
        logger.info(data.head())
        logger.info(f"Got OHLCV: {data.shape}.")

        assert isinstance(data, DataFrame)
        assert not data.is_empty()
