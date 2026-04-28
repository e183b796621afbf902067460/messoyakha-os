from enum import StrEnum


class FinamMarketEnum(StrEnum):
    MISX = "MISX"


class FinamIntervalEnum(StrEnum):
    ONE_HOUR = "TIME_FRAME_H1"
    FOUR_HOURS = "TIME_FRAME_H4"

    ONE_DAY = "TIME_FRAME_D"
