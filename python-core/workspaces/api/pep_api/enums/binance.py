from enum import StrEnum


class BinanceIntervalEnum(StrEnum):
	THIRTY_MINUTES = "30m"

	ONE_HOUR = "1h"
	TWO_HOURS = "2h"
	FOUR_HOURS = "4h"

	ONE_DAY = "1d"

	ONE_WEEK = "1w"


class BinanceMarketEnum(StrEnum):
	SPOT = "Spot"
	USDTM = "USDT-M"
