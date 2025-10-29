from pydantic import BaseModel


class BacktestParametersSchema(BaseModel):

    cash: float = 1_000_000
    commission: float = 0.000550
    spread: float = 0.0002
    margin: float = 1 / 5
