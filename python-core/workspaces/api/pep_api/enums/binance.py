from enum import StrEnum


class BinanceIntervalEnum(StrEnum):
	ONE_HOUR = "1h"
	FOUR_HOURS = "4h"

	ONE_DAY = "1d"


class BinanceMarketEnum(StrEnum):
	SPOT = "Spot"
	USDTM = "USDT-M"
