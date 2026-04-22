from attrs import define, field
from polars import DataFrame

from pep_api.adapters.finam import FinamAPIClient
from pep_api.schemas.finam import (
    FinamBarsEndpointSchema,
    FinamBarsHeadersSchema,
    FinamBarsInputSchema,
    FinamBarsOutputSchema,
    FinamBarsParametersSchema,
    FinamSessionsJsonSchema,
    FinamSessionsOutputSchema,
)


@define(slots=True, auto_attribs=True, kw_only=True)
class FinamService:
    _client: FinamAPIClient = field(init=False, factory=FinamAPIClient)

    async def get_ohlcv(self, input_schema: FinamBarsInputSchema) -> DataFrame:
        session: FinamSessionsOutputSchema = await self._client.sessions(
            json_schema=FinamSessionsJsonSchema(secret=input_schema.secret)
        )
        bars: list[FinamBarsOutputSchema] = await self._client.bars(
            endpoint_schema=FinamBarsEndpointSchema(ticker=input_schema.ticker),
            parameters_schema=FinamBarsParametersSchema(
                timeframe=input_schema.timeframe, start_time=input_schema.start_time, end_time=input_schema.end_time
            ),
            headers_schema=FinamBarsHeadersSchema(authorization=session.token),
        )
        return DataFrame([bar.model_dump() for bar in bars])
