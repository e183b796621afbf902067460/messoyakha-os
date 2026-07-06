from pydantic import HttpUrl


def options(access_key: str, secret_key: str, endpoint: HttpUrl, region: str) -> dict[str, str]:
    return {
        "aws_access_key_id": access_key,
        "aws_secret_access_key": secret_key,
        "aws_region": region,
        "aws_endpoint_url": endpoint.unicode_string(),
    }
