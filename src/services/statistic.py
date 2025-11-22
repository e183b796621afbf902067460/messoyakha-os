from itertools import combinations

from numpy import arange, exp, ndarray, searchsorted, sort
from pandas import DataFrame
from polars import DataFrame as PolarsDataFrame
from polars import col, from_pandas, sum_horizontal  # noqa: WPS347
from polars._typing import IntoExpr  # noqa: WPS436
from scipy.interpolate import interp1d


# pylint: disable=disallowed-name
def quantile_matching_fit(a: ndarray, b: ndarray) -> ndarray:  # noqa: WPS111
    sorted_a: ndarray = sort(a=a)
    sorted_b: ndarray = sort(a=b)

    cdf: ndarray = arange(1, len(b) + 1) / (len(b) + 1)

    fill_value: tuple[float, float] = (float(sorted_b[0]), float(sorted_b[-1]))
    interpolation: interp1d = interp1d(x=cdf, y=sorted_b, bounds_error=False, fill_value=fill_value)

    return interpolation(x=searchsorted(a=sorted_a, v=a, side="right") / (len(a) + 1))  # type: ignore[no-any-return]


# pylint: enable=disallowed-name


# pylint: disable=consider-using-generator
def weighted_average_by(
    dataframe: DataFrame | PolarsDataFrame, weights: dict[str, float], multiplier: int
) -> DataFrame:
    combos: list[list[str]] = [list(combo) for combo in combinations(iterable=list(weights.keys()), r=multiplier)]
    combos_length: int = len(combos)

    step: int = (int(combos_length / len(weights))) // 4 - 1
    combos = [combos[index] for index in range(0, combos_length, step if step > 0 else 1)]  # noqa: WPS509

    if combos:
        dataframe = from_pandas(data=dataframe)
        for combo in combos:
            weighted_average_column: str = f"{multiplier}_weighted_" + (
                str(sorted(combo))
                .replace("[", "")
                .replace("]", "")
                .replace("'", "")
                .replace(",", "_")
                .strip()  # noqa: WPS221
            )
            weighted_average_expression: dict[str, IntoExpr] = {
                weighted_average_column: (
                    sum_horizontal(col(column) * exp(weights[column]) for column in combo)
                    / sum([exp(weights[column]) for column in combo])
                )
            }
            dataframe = dataframe.lazy().with_columns(**weighted_average_expression)
        return dataframe.collect().to_pandas()
    return dataframe


# pylint: enable=consider-using-generator
