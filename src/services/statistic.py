from itertools import combinations
from typing import Final

from numpy import arange, argmin, array, ndarray, searchsorted, sort
from pandas import DataFrame, Series
from polars import DataFrame as PolarsDataFrame
from polars import col, from_pandas, sum_horizontal  # noqa: WPS347
from polars._typing import IntoExpr  # noqa: WPS436
from scipy.interpolate import interp1d
from scipy.stats import percentileofscore

_Q_THRESHOLD: Final[float] = 0.05


# pylint: disable=disallowed-name
def quantile_matching_fit(a: ndarray, b: ndarray) -> ndarray:  # noqa: WPS111
    sorted_a: ndarray = sort(a=a)
    sorted_b: ndarray = sort(a=b)

    cdf: ndarray = arange(1, len(b) + 1) / (len(b) + 1)

    fill_value: tuple[float, float] = (float(sorted_b[0]), float(sorted_b[-1]))
    interpolation: interp1d = interp1d(x=cdf, y=sorted_b, bounds_error=False, fill_value=fill_value)

    return interpolation(x=searchsorted(a=sorted_a, v=a, side="right") / (len(a) + 1))  # type: ignore[no-any-return]


# pylint: enable=disallowed-name


# pylint: disable=invalid-name, too-many-locals
def qq(tick: float, ticks: Series, q: Series, row: Series) -> float:  # noqa: WPS111
    percentile: float = percentileofscore(a=ticks, score=tick) / 100
    quantile: Series = q.quantile(percentile)

    q_percentiles: list[float] = []
    q_values: list[float] = []
    for index in quantile.index:
        value: float = row[index]

        q_percentile: float = percentileofscore(a=q[index], score=value) / 100
        q_percentiles.append(q_percentile)
        q_values.append(value)
    q_argmin: int = int(argmin(abs(q_percentiles - percentile)))  # type: ignore[operator]
    q_value: float = row[quantile.index[q_argmin]]

    q_diff: float = abs(q_value - tick)
    if q_diff > _Q_THRESHOLD:
        abs_argmin: int = int(argmin(abs(array(q_values) - tick)))
        abs_value: float = row[quantile.index[abs_argmin]]

        abs_diff: float = abs(abs_value - tick)
        q_value = q_value if q_diff < abs_diff else abs_value
    return q_value


# pylint: enable=invalid-name, too-many-locals


# pylint: disable=consider-using-generator
def weighted_average_by(
    dataframe: DataFrame | PolarsDataFrame, weights: dict[str, float], multiplier: int
) -> DataFrame:
    combos: list[list[str]] = [list(combo) for combo in combinations(iterable=list(weights.keys()), r=multiplier)]
    combos_length: int = len(combos)

    step: int = (int(combos_length / len(weights))) - 1
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
                    sum_horizontal(col(column) * weights[column] for column in combo)
                    / sum([weights[column] for column in combo])
                )
            }
            dataframe = dataframe.lazy().with_columns(**weighted_average_expression)
        return dataframe.collect().to_pandas()
    return dataframe


# pylint: enable=consider-using-generator
