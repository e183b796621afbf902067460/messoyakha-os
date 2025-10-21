from datetime import datetime, timedelta
from re import findall

from src.settings import settings

_YEARS_IN_RETROSPECTIVE: int = settings.TRIGGER_DATE.year - 2010  # noqa: WPS432


def determine_latest_timestamp(latest_timestamp: datetime | None) -> datetime:
    if latest_timestamp is None:
        return settings.TRIGGER_DATE - timedelta(  # type: ignore[no-any-return]
            days=settings.DAYS_IN_YEAR * _YEARS_IN_RETROSPECTIVE
        )
    return latest_timestamp + timedelta(seconds=1)


def format_s3_path(exchange: str, section: str, directory: str) -> str:
    return (
        f"s3://{settings.S3_BUCKET}/development/data/{directory}/"
        f"{settings.TICKER.lower()}/{exchange.lower()}/{section.lower()}/{settings.INTERVAL.lower()}"
    )


def format_s3_key(exchange: str, section: str, directory: str, filename: str | None = None) -> str:
    key: str = (
        f"development/data/{directory}/"
        f"{settings.TICKER.lower()}/{exchange.lower()}/{section.lower()}/{settings.INTERVAL.lower()}"
    )
    if filename:
        key = (
            f"development/data/{directory}/"
            f"{settings.TICKER.lower()}/{exchange.lower()}/{section.lower()}/{settings.INTERVAL.lower()}/{filename}"
        )
    return key


def findall_prefixes(strings: list[str]) -> list[str]:
    pattern: str = r"\b([a-zA-Z]+_\d+)_(?:open|high|low|close)\b"

    prefixes: list[str] = []
    for string in strings:
        match: list[str] = findall(pattern=pattern, string=string)
        if match and match[0] not in prefixes:
            prefixes.append(match[0])
    return prefixes
