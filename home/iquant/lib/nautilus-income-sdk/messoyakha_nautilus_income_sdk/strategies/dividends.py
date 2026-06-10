from nautilus_trader.accounting.accounts.base import Account
from nautilus_trader.model.data import DataType
from nautilus_trader.model.identifiers import ClientId
from nautilus_trader.model.objects import AccountBalance, Money
from nautilus_trader.trading.strategy import Strategy

from messoyakha_nautilus_income_sdk.schemas.dividends import DividendData


class DividendStrategy(Strategy):
    def __init__(self) -> None:
        self._dividend_client: ClientId = ClientId("dividend-client")

    def _subscribe_dividend(self) -> None:
        self.subscribe_data(DataType(DividendData), client_id=self._dividend_client)

    def _on_dividend(self, account: Account, dividend_data: DividendData) -> None:
        quantity: float = float(self.portfolio.net_position(dividend_data.nautilus_instrument_id))
        dividend: float = quantity * dividend_data.flow

        total: float = account.balance_total(dividend_data.nautilus_currency).as_double() + dividend
        free: float = account.balance_free(dividend_data.nautilus_currency).as_double() + dividend
        account.update_balances(
            [
                AccountBalance(
                    total=Money(total, dividend_data.nautilus_currency),
                    locked=Money(0, dividend_data.nautilus_currency),
                    free=Money(free, dividend_data.nautilus_currency),
                ),
            ]
        )
