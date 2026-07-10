from pydantic import BaseModel, Field, computed_field


class MOEXListedFromHTTPEndpointSchema(BaseModel):
    ticker: str = Field(exclude=True)

    @computed_field(alias="security", repr=False)
    def _security(self) -> str:
        return self.ticker

    def _cohere_http_endpoint(self) -> None: ...


class MOEXListedFromInputSchema(BaseModel):
    ticker: str
