from functools import partial

from attrs import define, field
from httpx import AsyncClient

from pep_sdk.adapters.common.bs import BSCrawlerBase
from pep_sdk.route import route
from pep_sdk.schemas.dohod import DohodDividendEndpointSchema


@define(slots=False, auto_attribs=True, kw_only=True)
class DohodBSCrawler(BSCrawlerBase):
    _session: AsyncClient = field(
        init=False, factory=partial(AsyncClient, base_url="https://www.dohod.ru", timeout=10, http2=True)
    )

    @route("/ik/analytics/dividend/{ticker}")
    async def dividend(self, endpoint_schema: DohodDividendEndpointSchema, **kwargs) -> None:  # noqa: ARG002
        await self._get(**kwargs)
