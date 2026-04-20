from abc import ABC

from attrs import define, field
from suds.client import Client


@define(slots=False, auto_attribs=True, kw_only=True)
class SOAPAPIClientBase(ABC):
	"""Base class for SOAP API clients."""

	_import: Client = field(init=False)
