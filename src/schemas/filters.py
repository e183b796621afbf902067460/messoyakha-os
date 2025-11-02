from pydantic import BaseModel


class QueryParametersBaseSchema(BaseModel):
    exchange: str
    section: str
    ticker: str
    interval: str

    def to_list(self) -> list[str]:
        return [self.exchange, self.section, self.ticker, self.interval]


class PathParametersBaseSchema(BaseModel):
    bucket: str
    directory: str


class OHLCQueryParametersSchema(QueryParametersBaseSchema):
    """Query parameters to fetch OHLC data."""


class OHLCPathParametersSchema(PathParametersBaseSchema):
    """Path parameters to fetch OHLC data."""


class LatestTimestampQueryParametersSchema(QueryParametersBaseSchema):
    """Query parameters to fetch latest timestamp."""


class LatestTimestampPathParametersSchema(PathParametersBaseSchema):
    """Path parameters to fetch latest timestamp."""


class MAQueryParametersSchema(QueryParametersBaseSchema):
    """Query parameters to fetch moving averages."""


class MAPathParametersSchema(PathParametersBaseSchema):
    """Path parameters to fetch moving averages."""


class ADXQueryParametersSchema(QueryParametersBaseSchema):
    """Query parameters to fetch average directional indexes."""


class ADXPathParametersSchema(PathParametersBaseSchema):
    """Path parameters to fetch average directional indexes."""


class SARTrialQueryParametersSchema(QueryParametersBaseSchema):
    """Query parameters to fetch SAR trials."""


class SARTrialPathParametersSchema(PathParametersBaseSchema):
    """Path parameters to fetch stops and reverses."""


class TradeQueryParametersSchema(QueryParametersBaseSchema):
    """Query parameters to fetch trades."""


class TradePathParametersSchema(PathParametersBaseSchema):
    """Path parameters to fetch trades."""
