from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.model.custom import customdataclass
from nautilus_trader.model.identifiers import InstrumentId
from pandas import DataFrame, Timestamp

from messoyakha_nautilus_income_sdk.schemas._common.cashflow import CashflowData


@customdataclass
class DividendData(CashflowData):
    id: str
    venue: str

    @property
    def nautilus_instrument_id(self) -> InstrumentId:
        return InstrumentId.from_str(f"{self.id}.{self.venue}")

    @classmethod
    def from_dividend(cls, id: str, venue: str, currency: str, dividend: float, timestamp: Timestamp) -> "DividendData":
        ts: int = dt_to_unix_nanos(dt=timestamp)

        dividend_data: DividendData = cls(id=id, venue=venue, flow=dividend, currency=currency)
        dividend_data._ts_event = ts
        dividend_data._ts_init = ts
        return dividend_data

    @staticmethod
    def from_dividends(dividends: DataFrame) -> list["DividendData"]:
        data: list[DividendData] = [
            DividendData.from_dividend(
                id=dividend.id,  # type: ignore[bad-argument-type]
                venue=dividend.venue,  # type: ignore[bad-argument-type]
                dividend=dividend.dividend,  # type: ignore[bad-argument-type]
                currency=dividend.currency,  # type: ignore[bad-argument-type]
                timestamp=dividend.timestamp,  # type: ignore[bad-argument-type]
            )
            for dividend in dividends.itertuples()
        ]
        return data
