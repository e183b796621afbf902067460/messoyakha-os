from src.settings import settings


def polars_storage_options() -> dict[str, str]:
    return {
        "aws_access_key_id": settings.S3_ACCESS_KEY_ID,
        "aws_secret_access_key": settings.S3_SECRET_ACCESS_KEY,
        "aws_region": settings.S3_REGION_NAME,
        "aws_endpoint_url": settings.S3_ENDPOINT_URL.unicode_string(),
    }
