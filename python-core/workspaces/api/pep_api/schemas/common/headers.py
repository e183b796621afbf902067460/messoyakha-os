from typing import Literal

from pydantic import BaseModel, Field, field_serializer


_BEARER: Literal["Bearer"] = "Bearer"


class HeadersSchemaBase(BaseModel):
    authorization: str = Field(serialization_alias="Authorization")

    @field_serializer("authorization")
    def add_bearer_to_authorization_at_serialization(self, authorization: str) -> str:
        if _BEARER not in authorization:
            return f"{_BEARER} {authorization}"
        return authorization
