from attrs import define
from suds.client import Client
from suds.xsd.doctor import ImportDoctor

from pep_clients.adapters.common.soap import SOAPAPIClientBase
from pep_clients.schemas.cbr import CBRKeyRateParametersSchema


@define(slots=False, auto_attribs=True, kw_only=True)
class CBRSOAPAPIClient(SOAPAPIClientBase):
    def __attrs_post_init__(self) -> None:
        self._schema.filter.add("http://web.cbr.ru/")
        self._client: Client = Client(
            url="http://www.cbr.ru/DailyInfoWebServ/DailyInfo.asmx?wsdl",
            doctor=ImportDoctor(self._schema),
            retxml=True,
        )

    def key_rate(self, parameters_schema: CBRKeyRateParametersSchema) -> bytes:
        return self._client.service.KeyRate(**parameters_schema.model_dump(by_alias=True))
