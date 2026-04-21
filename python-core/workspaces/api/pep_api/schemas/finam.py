from pydantic import BaseModel


class FinamSessionsJsonSchema(BaseModel):
	secret: str


class FinamSessionsOutputSchema(BaseModel):
	token: str
