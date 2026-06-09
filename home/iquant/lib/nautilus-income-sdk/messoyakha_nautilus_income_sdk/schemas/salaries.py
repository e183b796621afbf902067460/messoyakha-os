from datetime import timedelta
from itertools import product

from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.model.custom import customdataclass
from pandas import Timestamp, date_range

from messoyakha_nautilus_income_sdk.schemas._common.cashflow import CashflowData


@customdataclass
class SalaryData(CashflowData):
    @classmethod
    def from_salary(cls, salary: float, currency: str, timestamp: Timestamp) -> "SalaryData":
        ts: int = dt_to_unix_nanos(dt=timestamp)

        salary_data: SalaryData = cls(flow=salary, currency=currency)
        salary_data._ts_event = ts
        salary_data._ts_init = ts
        return salary_data

    @staticmethod
    def to_salaries(salary: float, currency: str, start_date: Timestamp, end_date: Timestamp) -> list["SalaryData"]:
        data: list[SalaryData] = []
        for month, day in product(date_range(start_date.replace(day=1), end_date, freq="MS"), (10, 25)):
            cutoff: Timestamp = month.replace(day=day)
            if cutoff.weekday() == 5:  # noqa: PLR2004
                cutoff -= timedelta(days=1)
            if cutoff.weekday() == 6:  # noqa: PLR2004
                cutoff -= timedelta(days=2)
            data.append(SalaryData.from_salary(salary=salary / 2, currency=currency, timestamp=cutoff))
        return data
