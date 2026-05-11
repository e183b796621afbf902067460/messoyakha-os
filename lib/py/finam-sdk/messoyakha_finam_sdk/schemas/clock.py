from pydantic import BaseModel

from messoyakha_finam_sdk.schemas._common.headers import FinamAuthorizationHeaderSchemaBase


class FinamClockHeadersSchema(FinamAuthorizationHeaderSchemaBase): ...


class FinamPingInputSchema(BaseModel):
    secret: str
