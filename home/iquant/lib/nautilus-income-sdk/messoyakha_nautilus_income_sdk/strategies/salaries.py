from nautilus_trader.accounting.accounts.base import Account
from nautilus_trader.model.data import DataType
from nautilus_trader.model.identifiers import ClientId
from nautilus_trader.model.objects import AccountBalance, Money
from nautilus_trader.trading.strategy import Strategy

from messoyakha_nautilus_income_sdk.schemas.salaries import SalaryData


class SalaryStrategy(Strategy):
    def __init__(self) -> None:
        self._salary_client: ClientId = ClientId("salary-client")

    def _subscribe_salary(self) -> None:
        self.subscribe_data(DataType(SalaryData), client_id=self._salary_client)

    def _on_salary(self, account: Account, salary_data: SalaryData) -> None:
        total: float = account.balance_total(salary_data.nautilus_currency).as_double() + salary_data.flow
        free: float = account.balance_free(salary_data.nautilus_currency).as_double() + salary_data.flow
        account.update_balances(
            [
                AccountBalance(
                    total=Money(total, salary_data.nautilus_currency),
                    locked=Money(0, salary_data.nautilus_currency),
                    free=Money(free, salary_data.nautilus_currency),
                ),
            ]
        )
