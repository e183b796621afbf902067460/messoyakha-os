from enum import StrEnum

from messoyakha_sdk.enums.intervals import MessoyakhaIntervalEnum


class FinamIntervalEnum(StrEnum):
    ONE_HOUR = "TIME_FRAME_H1"
    FOUR_HOURS = "TIME_FRAME_H4"

    ONE_DAY = "TIME_FRAME_D"


def finam_to_messoyakha_interval_mapping() -> dict[str, str]:
    return {
        FinamIntervalEnum.ONE_HOUR.value: MessoyakhaIntervalEnum.ONE_HOUR.value,
        FinamIntervalEnum.FOUR_HOURS.value: MessoyakhaIntervalEnum.FOUR_HOURS.value,
        FinamIntervalEnum.ONE_DAY.value: MessoyakhaIntervalEnum.ONE_DAY.value,
    }
