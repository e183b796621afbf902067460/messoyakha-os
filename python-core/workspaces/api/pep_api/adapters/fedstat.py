from functools import partial

from attrs import define, field
from httpx import AsyncClient, Response

from pep_api.adapters.common.http import HTTPAPIClientBase, route
from pep_api.schemas.fedstat import FedstatInflationRateJsonSchema, FedstatInflationRateParametersSchema


@define(slots=False, auto_attribs=True, kw_only=True)
class FedstatAPIClient(HTTPAPIClientBase):
    _session: AsyncClient = field(
        init=False,
        factory=partial(AsyncClient, base_url="https://www.fedstat.ru/indicator/data.do", timeout=10, http2=True),
    )

    @route("/")
    async def base(
        self,
        json_schema: FedstatInflationRateJsonSchema,
        parameters_schema: FedstatInflationRateParametersSchema,
        **kwargs,
    ) -> bytes:
        response: Response = await self._post(
            parameters=parameters_schema.model_dump(by_alias=True), json=json_schema.model_dump(by_alias=True), **kwargs
        )
        return response.content
