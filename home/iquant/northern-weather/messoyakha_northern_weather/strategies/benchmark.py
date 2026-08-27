from nautilus_trader.accounting.accounts.base import Account
from nautilus_trader.core.data import Data
from nautilus_trader.model.data import DataType

from messoyakha_nautilus_sdk.benchmarks.dca import DCAStrategy, DCAStrategyConfig
from messoyakha_nautilus_sdk.handlers.dividends import DividendsHandler
from messoyakha_nautilus_sdk.handlers.salaries import SalariesHandler
from messoyakha_nautilus_sdk.schemas.dividends import DividendIncomeData
from messoyakha_nautilus_sdk.schemas.salaries import SalaryIncomeData


class BenchmarkStrategy(DCAStrategy, DividendsHandler, SalariesHandler):
    def __init__(self, config: DCAStrategyConfig) -> None:
        DCAStrategy.__init__(self, config=config)

    def on_start(self) -> None:
        self.subscribe_data(DataType(SalaryIncomeData), client_id=self.config.client)
        self.subscribe_data(DataType(DividendIncomeData), client_id=self.config.client)

    def on_data(self, data: Data) -> None:  # type: ignore[bad-param-name-override]
        account: Account = self.portfolio.account(self.config.venue)
        if isinstance(data, DividendIncomeData):
            DividendsHandler.on_data(self, account=account, data=data)
        if isinstance(data, SalaryIncomeData):
            SalariesHandler.on_data(self, account=account, data=data)
