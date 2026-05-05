from functools import partial

from attrs import define, field
from bs4 import Tag
from crawlee.crawlers import BeautifulSoupCrawler, BeautifulSoupCrawlingContext
from crawlee.storage_clients.models import DatasetItemsListPage
from crawlee.storages import Dataset, RequestQueue
from httpx import AsyncClient

from pep_sdk.adapters.crawlers._common.bs import BSCrawlerBase
from pep_sdk.route import route
from pep_sdk.schemas.crawlers.dohod import (
    DohodDividendsContextSchema,
    DohodDividendsEndpointSchema,
    DohodDividendsOutputSchema,
)


@define(slots=False, auto_attribs=True, kw_only=True)
class DohodBSCrawler(BSCrawlerBase):
    _session: AsyncClient = field(init=False, factory=partial(AsyncClient, base_url="https://www.dohod.ru"))

    @route("/ik/analytics/dividend/{ticker}")
    async def dividend(
        self, endpoint_schema: DohodDividendsEndpointSchema, **kwargs
    ) -> list[DohodDividendsOutputSchema]:
        queue: RequestQueue = await self._get(**kwargs)
        crawler: BeautifulSoupCrawler = BeautifulSoupCrawler(request_manager=queue, configure_logging=False)

        @crawler.router.default_handler
        async def default_handler(context: BeautifulSoupCrawlingContext) -> None:
            for forecast in context.soup.select("table.content-table tr.forecast"):
                forecast.decompose()
            table: Tag = context.soup.find_all(name="table", attrs={"class": "content-table"})[1]
            table_values: list[list[Tag]] = [
                row.find_all("td") for row in table.find_all(name="tr") if not row.find("th")
            ]
            data: list[dict[str, str | None]] = [
                {"dividend": table_value[3].string, "timestamp": table_value[1].string} for table_value in table_values
            ]
            await context.push_data(data=data)

        await crawler.run()
        dataset: Dataset = await Dataset.open()
        response: DatasetItemsListPage = await dataset.get_data()
        context: DohodDividendsContextSchema = DohodDividendsContextSchema(ticker=endpoint_schema.ticker)
        return [
            DohodDividendsOutputSchema.model_validate(item, context=context.model_dump()) for item in response.items
        ]
