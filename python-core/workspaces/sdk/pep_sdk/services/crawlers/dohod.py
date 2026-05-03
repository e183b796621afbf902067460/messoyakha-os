from attrs import define, field
from polars import DataFrame, col

from pep_sdk.adapters.crawlers.dohod import DohodBSCrawler
from pep_sdk.schemas.crawlers.dohod import (
    DohodDividendEndpointSchema,
    DohodDividendInputSchema,
    DohodDividendOutputSchema,
)


@define(slots=True, auto_attribs=True, kw_only=True)
class DohodService:
    _crawler: DohodBSCrawler = field(init=False, factory=DohodBSCrawler)

    async def crawl_dividends(self, input_schema: DohodDividendInputSchema) -> DataFrame:
        dividends: list[DohodDividendOutputSchema] = await self._crawler.dividend(
            endpoint_schema=DohodDividendEndpointSchema(ticker=input_schema.ticker)
        )
        return DataFrame([dividend.model_dump() for dividend in dividends]).unique().sort(by=col("timestamp"))
