from enum import IntEnum

from messoyakha_sdk.enums.intervals import MessoyakhaIntervalEnum


class MOEXIntervalEnum(IntEnum):
    ONE_HOUR = 60
    FOUR_HOURS = 4

    ONE_DAY = 24


def moex_iss_to_messoyakha_interval_mapping() -> dict[int, str]:
    return {
        MOEXIntervalEnum.ONE_HOUR.value: MessoyakhaIntervalEnum.ONE_HOUR.value,
        MOEXIntervalEnum.FOUR_HOURS.value: MessoyakhaIntervalEnum.FOUR_HOURS.value,
        MOEXIntervalEnum.ONE_DAY.value: MessoyakhaIntervalEnum.ONE_DAY.value,
    }


def moex_iss_to_messoyakha_interval(interval: MOEXIntervalEnum | int) -> MessoyakhaIntervalEnum:
    mapping: dict[int, str] = moex_iss_to_messoyakha_interval_mapping()
    if isinstance(interval, MOEXIntervalEnum):
        return MessoyakhaIntervalEnum(mapping[interval.value])  # type: ignore[bad-index]
    if isinstance(interval, int):
        return MessoyakhaIntervalEnum(mapping[interval])
    raise ValueError(f"Got invalid type of interval: {type(interval)}.")
