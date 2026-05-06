from pep_sdk.schemas._common.headers import AuthorizationHeaderSchemaBase
from pep_sdk.schemas.clients.finam._common.secrets import FinamSecretsInputSchemaBase


class FinamClockHeadersSchema(AuthorizationHeaderSchemaBase): ...


class FinamPingInputSchema(FinamSecretsInputSchemaBase): ...
