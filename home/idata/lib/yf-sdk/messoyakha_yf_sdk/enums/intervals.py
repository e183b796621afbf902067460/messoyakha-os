from enum import StrEnum

from messoyakha_sdk.enums.intervals import MessoyakhaIntervalEnum


class YFIntervalEnum(StrEnum):
    ONE_HOUR = "1h"
    ONE_DAY = "1d"


def yf_to_messoyakha_interval_mapping() -> dict[str, str]:
    return {
        YFIntervalEnum.ONE_HOUR.value: MessoyakhaIntervalEnum.ONE_HOUR.value,
        YFIntervalEnum.ONE_DAY.value: MessoyakhaIntervalEnum.ONE_DAY.value,
    }


def yf_to_messoyakha_interval(interval: YFIntervalEnum | str) -> MessoyakhaIntervalEnum:
    mapping: dict[str, str] = yf_to_messoyakha_interval_mapping()
    if isinstance(interval, YFIntervalEnum):
        return MessoyakhaIntervalEnum(mapping[interval.value])
    if isinstance(interval, str):
        return MessoyakhaIntervalEnum(mapping[interval])
    raise ValueError(f"Got invalid type of interval: {type(interval)}.")
