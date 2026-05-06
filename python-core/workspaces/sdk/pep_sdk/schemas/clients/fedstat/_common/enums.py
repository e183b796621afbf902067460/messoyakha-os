from calendar import Month
from enum import StrEnum
from typing import Self


class FedstatMonthEnum(StrEnum):
    JANUARY = "1540283"
    FEBRUARY = "1540282"
    MARCH = "1540236"
    APRIL = "1540229"
    MAY = "1540235"
    JUNE = "1540234"
    JULY = "1540233"
    AUGUST = "1540228"
    SEPTEMBER = "1540276"
    OCTOBER = "1540273"
    NOVEMBER = "1540272"
    DECEMBER = "1540230"

    @classmethod
    def from_month(cls, month: int) -> Self:
        if month == Month.JANUARY.value:
            return cls(cls.JANUARY.value)
        if month == Month.FEBRUARY.value:
            return cls(cls.FEBRUARY.value)
        if month == Month.MARCH.value:
            return cls(cls.MARCH.value)
        if month == Month.APRIL.value:
            return cls(cls.APRIL.value)
        if month == Month.MAY.value:
            return cls(cls.MAY.value)
        if month == Month.JUNE.value:
            return cls(cls.JUNE.value)
        if month == Month.JULY.value:
            return cls(cls.JULY.value)
        if month == Month.AUGUST.value:
            return cls(cls.AUGUST.value)
        if month == Month.SEPTEMBER.value:
            return cls(cls.SEPTEMBER.value)
        if month == Month.OCTOBER.value:
            return cls(cls.OCTOBER.value)
        if month == Month.NOVEMBER.value:
            return cls(cls.NOVEMBER.value)
        if month == Month.DECEMBER.value:
            return cls(cls.DECEMBER.value)
        raise ValueError("Inappropriate month passed (pep-api).")
