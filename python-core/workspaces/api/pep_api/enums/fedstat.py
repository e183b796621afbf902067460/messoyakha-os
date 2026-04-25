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
        if month == cls.JANUARY.value:
            return cls(cls.JANUARY.value)
        if month == cls.FEBRUARY.value:
            return cls(cls.FEBRUARY.value)
        if month == cls.MARCH.value:
            return cls(cls.MARCH.value)
        if month == cls.APRIL.value:
            return cls(cls.APRIL.value)
        if month == cls.MAY.value:
            return cls(cls.MAY.value)
        if month == cls.JUNE.value:
            return cls(cls.JUNE.value)
        if month == cls.JULY.value:
            return cls(cls.JULY.value)
        if month == cls.AUGUST.value:
            return cls(cls.AUGUST.value)
        if month == cls.SEPTEMBER.value:
            return cls(cls.SEPTEMBER.value)
        if month == cls.OCTOBER.value:
            return cls(cls.OCTOBER.value)
        if month == cls.NOVEMBER.value:
            return cls(cls.NOVEMBER.value)
        if month == cls.DECEMBER.value:
            return cls(cls.DECEMBER.value)
        raise ValueError("Inappropriate month passed (pep-api).")
