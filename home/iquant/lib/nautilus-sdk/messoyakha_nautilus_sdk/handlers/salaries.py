from datetime import timedelta
from itertools import product

from nautilus_trader.accounting.accounts.base import Account
from nautilus_trader.model.objects import AccountBalance, Money
from nautilus_trader.trading.strategy import Strategy
from pandas import Timestamp, date_range

from messoyakha_nautilus_sdk.schemas.salaries import SalaryIncomeData


class SalariesHandler(Strategy):
    def on_data(self, account: Account, data: SalaryIncomeData) -> None:
        total: float = account.balance_total(data.nautilus_currency).as_double() + data.flow
        free: float = account.balance_free(data.nautilus_currency).as_double() + data.flow
        account.update_balances(
            [
                AccountBalance(
                    total=Money(total, data.nautilus_currency),
                    locked=Money(0, data.nautilus_currency),
                    free=Money(free, data.nautilus_currency),
                ),
            ]
        )


def salaries(
    income: float, currency: str, start_date: Timestamp, end_date: Timestamp, days: tuple[int, ...] = (10, 25)
) -> list[SalaryIncomeData]:
    data: list[SalaryIncomeData] = []
    for month, day in product(date_range(start_date.replace(day=1), end_date, freq="MS"), days):
        cutoff: Timestamp = month.replace(day=day)
        if cutoff.weekday() == 5:  # noqa: PLR2004
            cutoff -= timedelta(days=1)
        if cutoff.weekday() == 6:  # noqa: PLR2004
            cutoff -= timedelta(days=2)
        data.append(
            SalaryIncomeData._from_params(  # noqa: SLF001
                income=income / len(days), 
                currency=currency, 
                timestamp=cutoff
                )
        )
    return data
