from attrs import define, field
from polars import DataFrame, col

from messoyakha_dohod_sdk.adapters.dohod import DohodCrawleeWebClient
from messoyakha_dohod_sdk.schemas.dividends import (
    DohodDividendsEndpointSchema,
    DohodDividendsInputSchema,
    DohodDividendsOutputSchema,
)


@define(slots=True, auto_attribs=True, kw_only=True)
class DohodService:
    _client: DohodCrawleeWebClient = field(init=False, factory=DohodCrawleeWebClient)

    async def crawl_dividends(self, input_schema: DohodDividendsInputSchema) -> DataFrame:
        dividends: list[DohodDividendsOutputSchema] = await self._client.dividend(
            endpoint_schema=DohodDividendsEndpointSchema(ticker=input_schema.ticker)
        )
        return DataFrame([dividend.model_dump() for dividend in dividends]).unique().sort(by=col("timestamp"))
