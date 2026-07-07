from functools import partial

from attrs import define, field
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext
from crawlee.storage_clients.models import DatasetItemsListPage
from crawlee.storages import Dataset, RequestQueue
from httpx import AsyncClient
from pandas import to_datetime

from messoyakha_sdk.adapters.clients.web import CrawleeWebClientBase
from messoyakha_sdk.decorators.route import endpoint_route
from messoyakha_smart_lab_sdk.schemas.net_income import (
    SmartLabNetIncomeContextSchema,
    SmartLabNetIncomeEndpointSchema,
    SmartLabNetIncomeOutputSchema,
)


@define(slots=False, auto_attribs=True, kw_only=True)
class SmartLabCrawleeWebClient(CrawleeWebClientBase):
    _session: AsyncClient = field(init=False, factory=partial(AsyncClient, base_url="https://smart-lab.ru"))

    @endpoint_route("/q/{ticker}/MSFO/net_income")
    async def net_income(
        self, endpoint_schema: SmartLabNetIncomeEndpointSchema, **kwargs
    ) -> list[SmartLabNetIncomeOutputSchema]:
        queue: RequestQueue = await self._get(**kwargs)
        crawler: PlaywrightCrawler = PlaywrightCrawler(
            request_manager=queue, browser_type="chromium", headless=True, configure_logging=False
        )

        @crawler.router.default_handler
        async def default_handler(context: PlaywrightCrawlingContext) -> None:
            quarter_data: dict = (await context.page.evaluate("window.aQuarterData"))["diagram"]

            data: list = []
            for timestamp, net_income in zip(quarter_data["categories"], quarter_data["data"], strict=True):
                data.append({"timestamp": to_datetime(timestamp), "net_income": net_income["y"]})
            await context.push_data(data=data)

        await crawler.run()
        dataset: Dataset = await Dataset.open()
        response: DatasetItemsListPage = await dataset.get_data()
        context: SmartLabNetIncomeContextSchema = SmartLabNetIncomeContextSchema(ticker=endpoint_schema.ticker)
        return [
            SmartLabNetIncomeOutputSchema.model_validate(item, context=context.model_dump()) for item in response.items
        ]
