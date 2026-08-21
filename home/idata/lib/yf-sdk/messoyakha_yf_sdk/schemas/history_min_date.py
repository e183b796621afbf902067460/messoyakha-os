from pydantic import BaseModel


class YFHistoryMinDateInputSchema(BaseModel):
    ticker: str
