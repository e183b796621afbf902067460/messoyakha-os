from datetime import datetime, timedelta

from src.settings import settings


def determine_latest_timestamp(latest_timestamp: datetime | None) -> datetime:
    if latest_timestamp is None:
        return settings.TRIGGER_DATE - timedelta(days=settings.DAYS_IN_YEAR * settings.START_DATE)
    return latest_timestamp + timedelta(seconds=1)


def format_s3_path(exchange: str, section: str, directory: str) -> str:
    return (
        f"s3://{settings.S3_BUCKET}/development/data/{directory}/"
        f"{settings.TICKER.lower()}/{exchange.lower()}/{section.lower()}/{settings.INTERVAL.lower()}"
    )


def format_s3_prefix(exchange: str, section: str, directory: str) -> str:
    return (
        f"development/data/{directory}/"
        f"{settings.TICKER.lower()}/{exchange.lower()}/{section.lower()}/{settings.INTERVAL.lower()}"
    )
