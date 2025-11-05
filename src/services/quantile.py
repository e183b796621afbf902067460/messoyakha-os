from numpy import arange, argsort, array, isnan, ndarray, searchsorted, sort
from pandas import Series
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


def identify_nearest(value: float, values: list[float] | ndarray, rank: int = 0) -> float:
    values = array(object=values)
    values = values[~isnan(values)]

    distances: ndarray = abs(values - value)  # type: ignore[operator, arg-type]
    indices: ndarray = argsort(a=distances)

    return float(values[indices[rank]])


def identify_column(series: Series, target: str, columns: list[str]) -> str | None:
    for column in columns:
        if series[target] == series[column]:
            return column
    return None
