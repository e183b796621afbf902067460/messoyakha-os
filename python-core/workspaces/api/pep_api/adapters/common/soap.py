from abc import ABC

from attrs import define, field
from suds.client import Client


@define(slots=False, auto_attribs=True, kw_only=True)
class SOAPAPIClientBase(ABC):
	_client: Client = field(init=False)
