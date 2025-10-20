from datetime import datetime, timedelta

from src.settings import settings

_YEARS_IN_RETROSPECTIVE: int = settings.TRIGGER_DATE.year - 2010  # noqa: WPS432


def determine_latest_timestamp(latest_timestamp: datetime | None) -> datetime:
    if latest_timestamp is None:
        return settings.TRIGGER_DATE - timedelta(days=settings.DAYS_IN_YEAR * _YEARS_IN_RETROSPECTIVE)
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
