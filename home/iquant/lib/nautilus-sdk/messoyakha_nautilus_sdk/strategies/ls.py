from nautilus_trader.accounting.accounts.base import Account
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.identifiers import ClientId, InstrumentId, Venue
from nautilus_trader.model.objects import Currency, Quantity
from nautilus_trader.trading.strategy import Strategy
from numpy import floor


# https://nautilustrader.io/docs/python-api-latest/config.html#nautilus_trader.config.StrategyConfig
class LSStrategyConfig(StrategyConfig, frozen=True):
    id: InstrumentId
    bar: BarType
    product: str
    venue: Venue
    currency: Currency

    client: ClientId


# https://nautilustrader.io/docs/python-api-latest/trading.html#nautilus_trader.trading.Strategy
class LSStrategy(Strategy):
    def __init__(self, config: LSStrategyConfig) -> None:
        Strategy.__init__(self, config=config)

    def on_start(self) -> None:
        self.subscribe_bars(self.config.bar)

    def on_bar(self, bar: Bar) -> None:
        account: Account = self.portfolio.account(self.config.venue)
        cash: float = account.balance_total(self.config.currency).as_double()
        quantity: int = floor(cash / bar.close.as_double())
        if quantity > 0:
            self.submit_order(
                self.order_factory.market(
                    instrument_id=self.config.id,
                    order_side=OrderSide.BUY,
                    quantity=Quantity.from_int(quantity),
                )
            )
