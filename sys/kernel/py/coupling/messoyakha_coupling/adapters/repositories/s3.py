from abc import ABC

from attr import define, field
from polars import LazyFrame, SQLContext


@define(slots=False, auto_attribs=True, kw_only=True)
class S3PolarsRepositoryBase(ABC):
    _options: dict[str, str]
    _context: SQLContext = field(init=False, factory=SQLContext)

    def _query(self, query: str) -> LazyFrame:
        return self._context.execute(query=query, eager=False)
