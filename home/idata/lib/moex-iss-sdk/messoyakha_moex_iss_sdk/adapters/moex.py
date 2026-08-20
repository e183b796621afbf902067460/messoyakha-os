from abc import abstractmethod
from datetime import datetime, timezone
from functools import partial
from typing import TypeAlias

from attrs import define, field
from httpx import AsyncClient, Response

from messoyakha_moex_iss_sdk.schemas.history_security import (
    MOEXHistorySecurityContextSchema,
    MOEXHistorySecurityHTTPEndpointSchema,
    MOEXHistorySecurityOutputSchema,
    MOEXHistorySecurityParametersSchema,
)
from messoyakha_moex_iss_sdk.schemas.history_security_total import (
    MOEXHistorySecurityTotalContextSchema,
    MOEXHistorySecurityTotalHTTPEndpointSchema,
    MOEXHistorySecurityTotalOutputSchema,
    MOEXHistorySecurityTotalParametersSchema,
)
from messoyakha_moex_iss_sdk.schemas.listed_from import MOEXListedFromHTTPEndpointSchema
from messoyakha_sdk.adapters.clients.http import HTTPAPIClientBase
from messoyakha_sdk.decorators.route import endpoint_route


@define(slots=False, auto_attribs=True, kw_only=True)
class _MOEXAPIClientBase(HTTPAPIClientBase):
    _session: AsyncClient = field(
        init=False, factory=partial(AsyncClient, base_url="https://iss.moex.com", timeout=60, http2=True)
    )

    @staticmethod
    @abstractmethod
    def _parse_history_security(history_security: list) -> list:
        raise NotImplementedError("`_parse_history_security` method not implemented.")

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
            MOEXHistorySecurityOutputSchema.model_validate(
                self._parse_history_security(history_security=history_security), context=context.model_dump()
            )
            for history_security in response.json()["history"]["data"]
        ]

    # https://iss.moex.com/iss/reference/193
    @endpoint_route("/iss/securities/{security}.json")
    async def listed_from(
        self,
        endpoint_schema: MOEXListedFromHTTPEndpointSchema,  # noqa: ARG002
        **kwargs,
    ) -> datetime:
        response: Response = await self._get(**kwargs)
        return min(
            datetime.strptime(board[12], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            for board in response.json()["boards"]["data"]
        )


@define(slots=False, auto_attribs=True, kw_only=True)
class MOEXStockIndexAPIClient(_MOEXAPIClientBase):
    @staticmethod
    def _parse_history_security(history_security: list) -> list:
        return history_security

    # https://iss.moex.com/iss/reference/439
    @endpoint_route("/iss/history/engines/stock/markets/index/securities/{security}.json")
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


@define(slots=False, auto_attribs=True, kw_only=True)
class MOEXStockSharesAPIClient(_MOEXAPIClientBase):
    @staticmethod
    def _parse_history_security(history_security: list) -> list:
        result: list = [None] * 18
        result[2] = history_security[1]
        result[5] = history_security[11]
        result[6] = history_security[6]
        result[7] = history_security[8]
        result[8] = history_security[7]
        result[17] = history_security[12]
        return result

    # https://iss.moex.com/iss/reference/439
    @endpoint_route("/iss/history/engines/stock/markets/shares/securities/{security}.json")
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

    # https://iss.moex.com/iss/reference/509
    @endpoint_route("/iss/history/engines/stock/totals/boards/MRKT/securities/{security}.json")
    async def history_security_total(
        self,
        endpoint_schema: MOEXHistorySecurityTotalHTTPEndpointSchema,
        parameters_schema: MOEXHistorySecurityTotalParametersSchema,
        **kwargs,
    ) -> list[MOEXHistorySecurityTotalOutputSchema]:
        response: Response = await self._get(
            parameters=(
                parameters_schema.model_dump(by_alias=True)
                if parameters_schema.start_time and parameters_schema.end_time
                else None
            ),
            **kwargs,
        )
        context: MOEXHistorySecurityTotalContextSchema = MOEXHistorySecurityTotalContextSchema(
            ticker=endpoint_schema.ticker,
            currency=parameters_schema.currency,
        )
        return [
            MOEXHistorySecurityTotalOutputSchema.model_validate(
                history_security_total,
                context=context.model_dump(),
            )
            for history_security_total in response.json()["security"]["data"]
        ]


MOEXAPIClient: TypeAlias = MOEXStockIndexAPIClient | MOEXStockSharesAPIClient
