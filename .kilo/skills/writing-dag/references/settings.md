# Settings

## Hierarchy

```
S3SettingsBase                     # ACCESS_KEY, SECRET_KEY, BUCKET, ENDPOINT, REGION
  └── IcebergSettingsBase          # catalog (load_catalog), uri (s3://<BUCKET>)
        └── DLHSettings            # NAMESPACE, TRIGGER_DATE, BUCKET
              ├── CBRKeyRatesDLHSettings   # CATCH_UP_DATE
              └── DohodDividendsDLHSettings # TICKERS
```

`IcebergSettingsBase` in `messoyakha_coupling.settings.storages.s3` combines pydantic-settings with PyIceberg catalog loading. It reads S3 credentials from env vars (`S3_ACCESS_KEY`, `S3_SECRET_KEY`, etc.) and exposes a `catalog` property that returns a pre-configured `pyiceberg.catalog.Catalog`.

## DAG Settings

At the DAG package root, define a base settings class:

### S3-Backed DAG

```python
from datetime import datetime, timezone
from messoyakha_coupling.settings.storages.s3 import IcebergSettingsBase

class DLHSettings(IcebergSettingsBase):
    NAMESPACE: str = "dlh"
    BUCKET: str = "f8e90488-f511555d-274b-4258-bffc-572dd1900382"
    ACCESS_KEY: str
    SECRET_KEY: str
    TRIGGER_DATE: datetime = datetime.now(tz=timezone.utc)
```

### Research DAG (no S3)

```python
from datetime import datetime, timezone
from pydantic_settings import BaseSettings

class ResearchSettings(BaseSettings):
    TRIGGER_DATE: datetime = datetime.now(tz=timezone.utc)
```

## Source-Specific Extensions

Each source domain extends the DAG settings with its own defaults, defined in its service module:

**Iterative source** — adds `CATCH_UP_DATE` as fallback for initial loads when the Iceberg table is empty:

```python
class CBRKeyRatesDLHSettings(DLHSettings):
    CATCH_UP_DATE: datetime = datetime(year=2022, month=1, day=1, tzinfo=timezone.utc)
```

**Overwrite source** — no `CATCH_UP_DATE`; may add domain-specific fields:

```python
class DohodDividendsDLHSettings(DLHSettings):
    TICKERS: list[str] = ["SIBN", "ROSN", "TRNFP", "PHOR", "PLZL", "SBER"]
```
