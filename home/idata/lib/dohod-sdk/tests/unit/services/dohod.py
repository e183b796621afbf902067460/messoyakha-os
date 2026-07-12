import pytest
from loguru import logger
from polars import Config, DataFrame

from messoyakha_dohod_sdk.schemas.dividends import DohodDividendsInputSchema
from messoyakha_dohod_sdk.services.dohod import DohodService


Config.set_tbl_cols(-1)
Config.set_fmt_str_lengths(1024)


class TestDohodService:
    @pytest.mark.asyncio
    async def test_crawl_dividends(self) -> None:
        service: DohodService = DohodService()
        data: DataFrame = await service.crawl_dividends(
            input_schema=DohodDividendsInputSchema(
                ticker="SBER",
            )
        )
        logger.info(data.head())
        logger.info(f"Got dividends: {data.shape}.")

        assert isinstance(data, DataFrame)
        assert not data.is_empty()
