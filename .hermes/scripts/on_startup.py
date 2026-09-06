from pathlib import Path

import httpx
from loguru import logger
from openviking_sdk import SyncHTTPClient
from openviking_sdk.errors import NotFoundError, OpenVikingError
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, HttpUrl


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(Path(__file__).resolve().parent / ".env",)
    )

    OPENVIKING_ENDPOINT: HttpUrl = Field(default=HttpUrl("http://0.0.0.0:1933"))
    OPENVIKING_API_KEY: str
    OPENVIKING_TIMEOUT: int = Field(default=604800)

    OPENVIKING_ACCOUNT: str = Field(default="default")
    OPENVIKING_USER: str = Field(default="default")
    OPENVIKING_AGENT: str = Field(default="hermes")


def _parent_uri_for(pdf: Path, books_directory: Path) -> str:
    books_resource_uri: str = "viking://resources/books"
    relative = pdf.relative_to(books_directory)
    if relative.parent == Path():
        return books_resource_uri
    return f"{books_resource_uri}/{relative.parent.as_posix()}"


def main(settings: Settings) -> None:
    books_directory = Path.cwd() / ".hermes" / ".openviking" / "resources" / "books"

    client = SyncHTTPClient(
        url=settings.OPENVIKING_ENDPOINT.encoded_string(),
        api_key=settings.OPENVIKING_API_KEY,
        account=settings.OPENVIKING_ACCOUNT,
        user=settings.OPENVIKING_USER,
        agent_id=settings.OPENVIKING_AGENT,
        timeout=settings.OPENVIKING_TIMEOUT,
    )
    client.initialize()

    for pdf in sorted(books_directory.rglob("*.pdf")):
        parent_uri = _parent_uri_for(pdf, books_directory)
        try:
            try:
                entries = client.ls(parent_uri, simple=True)
            except NotFoundError:
                entries = []
            if any(Path(entry).name.startswith(pdf.stem) for entry in entries):
                logger.info(f"{pdf.name} is already indexed at {parent_uri}.")
                continue
            logger.info(f"{pdf.name} is indexing.")
            client.add_resource(
                path=str(pdf),
                parent=parent_uri,
                options={
                    "reason": "Book library sync on Hermes startup",
                    "processing_mode": "vectors_only",
                    "create_parent": True,
                    "directly_upload_media": False,
                },
                timeout=settings.OPENVIKING_TIMEOUT,
                wait=True,
            )
        except (OpenVikingError, httpx.HTTPError, OSError) as error:
            logger.error(
                f"Failed to index {pdf.name} ({type(error).__name__}: {error}); it will be retried on the next run."
            )
    client.close()


if __name__ == "__main__":
    main(
        settings=Settings()
    )
