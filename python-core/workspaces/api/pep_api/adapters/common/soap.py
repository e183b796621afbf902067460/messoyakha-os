from abc import ABC
from functools import partial

from attrs import define, field
from suds.xsd.doctor import Import


@define(slots=False, auto_attribs=True, kw_only=True)
class SOAPAPIClientBase(ABC):
	_schema: Import = field(init=False, factory=partial(Import, ns="http://www.w3.org/2001/XMLSchema"))
