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


class MAQueryParametersSchema(QueryParametersBaseSchema):
    """Query parameters to fetch moving averages."""


class MAPathParametersSchema(PathParametersBaseSchema):
    directory: str = "moving-averages"


class ADXQueryParametersSchema(QueryParametersBaseSchema):
    """Query parameters to fetch average directional indexes."""


class ADXPathParametersSchema(PathParametersBaseSchema):
    directory: str = "average-directional-indexes"


class PDIQueryParametersSchema(QueryParametersBaseSchema):
    """Query parameters to fetch average directional indexes."""


class PDIPathParametersSchema(PathParametersBaseSchema):
    directory: str = "plus-directional-indexes"


class MDIQueryParametersSchema(QueryParametersBaseSchema):
    """Query parameters to fetch average directional indexes."""


class MDIPathParametersSchema(PathParametersBaseSchema):
    directory: str = "minus-directional-indexes"


class RSIQueryParametersSchema(QueryParametersBaseSchema):
    """Query parameters to fetch ratios."""


class RSIPathParametersSchema(PathParametersBaseSchema):
    directory: str = "rsi"


class AroonQueryParametersSchema(QueryParametersBaseSchema):
    """Query parameters to fetch aroons."""


class AroonPathParametersSchema(PathParametersBaseSchema):
    directory: str = "aroons"


class BinaryQueryParametersSchema(QueryParametersBaseSchema):
    """Query parameters to fetch binaries."""


class BinaryPathParametersSchema(PathParametersBaseSchema):
    directory: str = "binaries"


class StreakQueryParametersSchema(QueryParametersBaseSchema):
    """Query parameters to fetch streaks."""


class StreakPathParametersSchema(PathParametersBaseSchema):
    directory: str = "streaks"


class SARTrialQueryParametersSchema(QueryParametersBaseSchema):
    """Query parameters to fetch SAR trials."""


class SARTrialPathParametersSchema(PathParametersBaseSchema):
    directory: str = "stop-and-reverse-trials"


class TradeQueryParametersSchema(QueryParametersBaseSchema):
    """Query parameters to fetch trades."""


class TradePathParametersSchema(PathParametersBaseSchema):
    directory: str = "trades"


class MLModelQueryParametersSchema(QueryParametersBaseSchema):
    """Query parameters to fetch ML-model."""


class MLModelPathParametersSchema(PathParametersBaseSchema):
    directory: str = Field(default=None)
