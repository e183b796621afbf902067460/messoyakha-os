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
        if month == 1:
            return cls(cls.JANUARY.value)
        if month == cls.FEBRUARY.value:
            return cls(cls.FEBRUARY.value)
        if month == 3:  # noqa: PLR2004
            return cls(cls.MARCH.value)
        if month == 4:  # noqa: PLR2004
            return cls(cls.APRIL.value)
        if month == 5:  # noqa: PLR2004
            return cls(cls.MAY.value)
        if month == 6:  # noqa: PLR2004
            return cls(cls.JUNE.value)
        if month == 7:  # noqa: PLR2004
            return cls(cls.JULY.value)
        if month == 8:  # noqa: PLR2004
            return cls(cls.AUGUST.value)
        if month == 9:  # noqa: PLR2004
            return cls(cls.SEPTEMBER.value)
        if month == 10:  # noqa: PLR2004
            return cls(cls.OCTOBER.value)
        if month == 11:  # noqa: PLR2004
            return cls(cls.NOVEMBER.value)
        if month == 12:  # noqa: PLR2004
            return cls(cls.DECEMBER.value)
        raise ValueError("Inappropriate month passed (pep-api).")
