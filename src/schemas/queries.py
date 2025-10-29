from pydantic import BaseModel


class _QueryParametersBaseSchema(BaseModel):
    exchange: str
    section: str
    ticker: str
    interval: str

    def to_list(self) -> list[str]:
        return [self.exchange, self.section, self.ticker, self.interval]


class OHLCQueryParametersSchema(_QueryParametersBaseSchema):
    """Query parameters to fetch OHLC data."""


class LatestTimestampQueryParametersSchema(_QueryParametersBaseSchema):
    """Query parameters to fetch latest timestamp."""


class MAQueryParametersSchema(_QueryParametersBaseSchema):
    """Query parameters to fetch moving averages."""


class ADXQueryParametersSchema(_QueryParametersBaseSchema):
    """Query parameters to fetch ADX."""


class SARQueryParametersSchema(_QueryParametersBaseSchema):
    """Query parameters to fetch ADX."""


class SARTrialsQueryParametersSchema(_QueryParametersBaseSchema):
    """Query parameters to fetch SAR trials."""
