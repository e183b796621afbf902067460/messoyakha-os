from attrs import define
from suds.client import Client
from suds.xsd.doctor import Import, ImportDoctor

from pep_api.adapters.common.soap import SOAPAPIClientBase
from pep_api.schemas.cbr import CBRKeyRateParametersSchema


@define(slots=False, auto_attribs=True, kw_only=True)
class CBRSOAPAPIClient(SOAPAPIClientBase):
	def __attrs_post_init__(self) -> None:
		import_xml_schema: Import = Import("http://www.w3.org/2001/XMLSchema")
		import_xml_schema.filter.add("http://web.cbr.ru/")
		import_xml_schema_doctor: ImportDoctor = ImportDoctor(import_xml_schema)

		self._client: Client = Client(
			url="http://www.cbr.ru/DailyInfoWebServ/DailyInfo.asmx?wsdl",
			doctor=import_xml_schema_doctor,
			retxml=True,
			headers={"User-Agent": "Mozilla"},
		)

	# TODO: CBRKeyRateOutputSchema (pydantic-xml)
	def key_rate(self, parameters_schema: CBRKeyRateParametersSchema) -> bytes:
		return self._client.service.KeyRate(**parameters_schema.model_dump(by_alias=True))
