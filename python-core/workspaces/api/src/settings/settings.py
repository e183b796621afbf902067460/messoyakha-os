from datetime import datetime

from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
	TRIGGER_DATE: datetime = datetime.now()

	MILLISECONDS_IN_SECOND: int = 10**3
	DAYS_IN_YEAR: int = 365

	class Config:
		case_sensitive = True


settings: AppSettings = AppSettings()
