from abc import ABC, abstractmethod

from attr import attrs
from polars import DataFrame

from src.adapters.clients.common.api_base import APIClientBase
from src.schemas.common.base import APIBaseSchema


@attrs(slots=True, auto_attribs=True, kw_only=True)
class APIBaseService(ABC):

    _client: APIClientBase

    @abstractmethod
    async def get_ohlc(self, input_schema: APIBaseSchema) -> DataFrame:
        raise NotImplementedError
