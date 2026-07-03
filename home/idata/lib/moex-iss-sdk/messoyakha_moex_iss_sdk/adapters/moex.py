from functools import partial
from typing import TypeAlias

from attrs import define, field
from httpx import AsyncClient, Response

from messoyakha_coupling.adapters.clients.http import HTTPAPIClientBase
from messoyakha_coupling.decorators.clients.http import route
from messoyakha_moex_iss_sdk.schemas.history_security import (
    MOEXHistorySecurityContextSchema,
    MOEXHistorySecurityHTTPEndpointSchema,
    MOEXHistorySecurityOutputSchema,
    MOEXHistorySecurityParametersSchema,
)


@define(slots=False, auto_attribs=True, kw_only=True)
class _MOEXAPIClientBase(HTTPAPIClientBase):
    _session: AsyncClient = field(
        init=False, factory=partial(AsyncClient, base_url="https://iss.moex.com", timeout=10, http2=True)
    )

    async def _history_security(
        self,
        endpoint_schema: MOEXHistorySecurityHTTPEndpointSchema,
        parameters_schema: MOEXHistorySecurityParametersSchema,
        **kwargs,
    ) -> list[MOEXHistorySecurityOutputSchema]:
        response: Response = await self._get(
            parameters=parameters_schema.model_dump(by_alias=True),
            **kwargs,
        )
        context: MOEXHistorySecurityContextSchema = MOEXHistorySecurityContextSchema(
            ticker=endpoint_schema.ticker,
            currency=parameters_schema.currency,
            product=parameters_schema.product,
            interval=parameters_schema.interval,
        )
        return [
            MOEXHistorySecurityOutputSchema.model_validate(history_security, context=context.model_dump())
            for history_security in response.json()["history"]["data"]
        ]


@define(slots=False, auto_attribs=True, kw_only=True)
class MOEXStockIndexAPIClient(_MOEXAPIClientBase):
    # https://iss.moex.com/iss/reference/439
    @route("/iss/history/engines/stock/markets/index/securities/{security}.json")
    async def history_security(
        self,
        endpoint_schema: MOEXHistorySecurityHTTPEndpointSchema,
        parameters_schema: MOEXHistorySecurityParametersSchema,
        **kwargs,
    ) -> list[MOEXHistorySecurityOutputSchema]:
        return await super()._history_security(
            endpoint_schema=endpoint_schema,
            parameters_schema=parameters_schema,
            **kwargs,
        )


MOEXAPIClient: TypeAlias = MOEXStockIndexAPIClient
