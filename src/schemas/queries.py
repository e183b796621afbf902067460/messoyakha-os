from pydantic import BaseModel


class _QueryParametersBaseSchema(BaseModel):
    exchange: str
    section: str
    ticker: str
    interval: str

    def to_list(self) -> list[str]:
        return [self.exchange, self.section, self.ticker, self.interval]


class CandlesticksQueryParametersSchema(_QueryParametersBaseSchema):
    """Query parameters to fetch candlestick data."""


class LatestTimestampQueryParametersSchema(_QueryParametersBaseSchema):
    """Query parameters to fetch latest timestamp."""


class MovingAveragesQueryParametersSchema(_QueryParametersBaseSchema):
    """Query parameters to fetch moving averages."""


class ADXQueryParametersSchema(_QueryParametersBaseSchema):
    """Query parameters to fetch ADX."""
