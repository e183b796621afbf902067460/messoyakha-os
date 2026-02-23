from pydantic import BaseModel, Field


class QueryParametersBaseSchema(BaseModel):
    exchange: str
    section: str
    ticker: str
    interval: str

    def to_list(self) -> list[str]:
        return [self.exchange, self.section, self.ticker, self.interval]


class PathParametersBaseSchema(BaseModel):
    bucket: str
    directory: str = Field(init=False)


class OHLCQueryParametersSchema(QueryParametersBaseSchema):
    """Query parameters to fetch OHLC data."""


class OHLCPathParametersSchema(PathParametersBaseSchema):
    directory: str = "candlesticks"


class LatestTimestampQueryParametersSchema(QueryParametersBaseSchema):
    """Query parameters to fetch latest timestamp."""


class LatestTimestampPathParametersSchema(PathParametersBaseSchema):
    directory: str = "candlesticks"
