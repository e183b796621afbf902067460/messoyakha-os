from attrs import define, field
from polars import DataFrame, col

from pep_sdk.adapters.crawlers.dohod import DohodBSCrawler
from pep_sdk.schemas.crawlers.dohod import (
    DohodDividendsEndpointSchema,
    DohodDividendsInputSchema,
    DohodDividendsOutputSchema,
)


@define(slots=True, auto_attribs=True, kw_only=True)
class DohodService:
    _crawler: DohodBSCrawler = field(init=False, factory=DohodBSCrawler)

    async def crawl_dividends(self, input_schema: DohodDividendsInputSchema) -> DataFrame:
        dividends: list[DohodDividendsOutputSchema] = await self._crawler.dividend(
            endpoint_schema=DohodDividendsEndpointSchema(ticker=input_schema.ticker)
        )
        return DataFrame([dividend.model_dump() for dividend in dividends]).unique().sort(by=col("timestamp"))
