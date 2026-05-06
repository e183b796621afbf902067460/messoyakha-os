from datetime import datetime

from pydantic import BaseModel, Field, computed_field

from pep_sdk.schemas.clients.fedstat._common.enums import FedstatMonthEnum


class FedstatInflationRateParametersSchema(BaseModel):
    id: str = Field(init=False, default="33568")


class _FedstatDataSchemaBase(BaseModel):
    format: str = Field(init=False, default="excel")


class FedstatInflationRateDataSchema(_FedstatDataSchemaBase):
    start_date: datetime = Field(exclude=True)
    end_date: datetime = Field(exclude=True)

    @computed_field(alias="lineObjectIds", repr=False)
    @property
    def _line_object_ids(self) -> list[str]:
        return [
            "0",
            "30611",
            "57831",
        ]

    @computed_field(alias="columnObjectIds", repr=False)
    @property
    def _column_object_ids(self) -> list[str]:
        return [
            "3",
            "33560",
            "57937",
        ]

    @computed_field(alias="selectedFilterIds", repr=False)
    @property
    def _selected_filter_ids(self) -> list[str]:
        selected_filter_ids: list[str] = [
            "0_33568",
            "30611_950473",
            "57831_1688487",
            "57937_1704140",
        ]

        selected_year_filter_ids: list[str] = [f"3_{year}" for year in self._date_range_to_list_of_years()]
        selected_filter_ids.extend(selected_year_filter_ids)

        selected_month_filter_ids: list[str] = [
            f"33560_{month.value}" for month in self._date_range_to_list_of_months()
        ]
        selected_filter_ids.extend(selected_month_filter_ids)
        return selected_filter_ids

    def _date_range_to_list_of_years(self) -> list[int]:
        return list(range(self.start_date.year, self.end_date.year + 1))

    def _date_range_to_list_of_months(self) -> list[FedstatMonthEnum]:
        if self.end_date.year - self.start_date.year > 1:
            return [FedstatMonthEnum.from_month(month=month) for month in range(1, 13)]

        start_month: int = self.start_date.month
        end_month: int = self.end_date.month

        if self.start_date.year == self.end_date.year:
            return [FedstatMonthEnum.from_month(month=month) for month in range(start_month, end_month + 1)]

        months: list[FedstatMonthEnum] = [FedstatMonthEnum.from_month(month=month) for month in range(start_month, 13)]
        months.extend([FedstatMonthEnum.from_month(month=month) for month in range(1, end_month + 1)])
        return months


class FedstatInflationRateInputSchema(BaseModel):
    start_date: datetime
    end_date: datetime
