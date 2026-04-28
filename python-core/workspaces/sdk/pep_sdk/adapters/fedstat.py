from functools import partial

from attrs import define, field
from httpx import AsyncClient, Response

from pep_sdk.adapters.common.http import HTTPAPIClientBase
from pep_sdk.schemas.fedstat import FedstatInflationRateDataSchema, FedstatInflationRateParametersSchema


@define(slots=False, auto_attribs=True, kw_only=True)
class FedstatAPIClient(HTTPAPIClientBase):
    _session: AsyncClient = field(
        init=False,
        factory=partial(AsyncClient, base_url="https://www.fedstat.ru/indicator/data.do", timeout=10, http2=True),
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
