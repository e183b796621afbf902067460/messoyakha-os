from functools import partial

from attrs import define, field
from suds.client import Client
from suds.xsd.doctor import Import, ImportDoctor

from pep_api.adapters.common.soap import SOAPAPIClientBase


@define(slots=False, auto_attribs=True, kw_only=True)
class CBRSOAPAPIClient(SOAPAPIClientBase):
	"""CBR SOAP API client."""

	_client: Client = field(
		init=False,
		factory=partial(
			Client,
			url="http://www.cbr.ru/DailyInfoWebServ/DailyInfo.asmx?wsdl",
			retxml=True,
			headers={"User-Agent": "Mozilla"},
		),
	)

	def __attrs_post_init__(self) -> None:
		self._import_xml_schema = Import("http://www.w3.org/2001/XMLSchema")
		self._import_xml_schema.filter.add("http://web.cbr.ru/")
		self._import_xml_schema_doctor = ImportDoctor(self._import_xml_schema)
		self._client.set_options(doctor=self._import_xml_schema_doctor)
