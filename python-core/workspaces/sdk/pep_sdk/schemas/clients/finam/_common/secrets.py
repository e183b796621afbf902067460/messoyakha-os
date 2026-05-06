from pydantic import BaseModel


class FinamSecretsInputSchemaBase(BaseModel):
    secret: str
