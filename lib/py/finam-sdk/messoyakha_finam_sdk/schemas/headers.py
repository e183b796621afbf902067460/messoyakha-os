from pydantic import BaseModel, Field, field_serializer


class AuthorizationHeaderSchemaBase(BaseModel):
    authorization: str = Field(serialization_alias="Authorization")

    @field_serializer("authorization")
    def _add_bearer_to_authorization(self, authorization: str) -> str:
        bearer: str = "Bearer"
        if bearer not in authorization:
            return f"{bearer} {authorization}"
        return authorization
