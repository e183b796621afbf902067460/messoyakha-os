from nautilus_trader.accounting.accounts.base import Account
from nautilus_trader.model.objects import AccountBalance, Money
from nautilus_trader.trading.strategy import Strategy

from messoyakha_nautilus_sdk.schemas.dividends import DividendIncomeData


class DividendsHandler(Strategy):
    def on_data(self, account: Account, data: DividendIncomeData) -> None:
        quantity: float = float(self.portfolio.net_position(data.nautilus_instrument_id))
        dividend: float = quantity * data.flow

        total: float = account.balance_total(data.nautilus_currency).as_double() + dividend
        free: float = account.balance_free(data.nautilus_currency).as_double() + dividend
        account.update_balances(
            [
                AccountBalance(
                    total=Money(total, data.nautilus_currency),
                    locked=Money(0, data.nautilus_currency),
                    free=Money(free, data.nautilus_currency),
                ),
            ]
        )
