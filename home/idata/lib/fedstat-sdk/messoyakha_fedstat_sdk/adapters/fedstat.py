from functools import partial

from attrs import define, field
from httpx import AsyncClient, Response

from messoyakha_fedstat_sdk.schemas.inflation_rate import (
    FedstatInflationRateDataSchema,
    FedstatInflationRateParametersSchema,
)
from messoyakha_sdk.adapters.clients.http import HTTPAPIClientBase


@define(slots=False, auto_attribs=True, kw_only=True)
class FedstatAPIClient(HTTPAPIClientBase):
    _session: AsyncClient = field(
        init=False,
        factory=partial(AsyncClient, base_url="https://www.fedstat.ru/indicator/data.do", timeout=60, http2=True),
    )

    async def inflation_rate(
        self,
        data_schema: FedstatInflationRateDataSchema,
        parameters_schema: FedstatInflationRateParametersSchema,
        **kwargs,
    ) -> bytes:
        response: Response = await self._post(
            data=data_schema.model_dump(by_alias=True), parameters=parameters_schema.model_dump(), **kwargs
        )
        return response.content
