from itertools import combinations
from typing import Final

from numpy import any as numpy_any
from numpy import argmin, array, floor, ndarray
from numpy import sum as numpy_sum
from numpy import zeros
from pandas import Series

_RANK_WEIGHT: Final[float] = 0.25
_POTENTIAL_THRESHOLD: Final[float] = 0.99


def _identify_target(row: Series, matching_columns: list[str], target_column: str = "rank") -> str | None:
    for column in matching_columns:
        if row[target_column] == row[column]:
            return column
    return None


# pylint: disable=too-complex
def determine_matching_columns(  # noqa: WPS231
    row: dict[str, int | float], ma_prefixes: list[str], potential_columns: list[str]
) -> list[str]:
    matching_columns: list[str] = []
    for ma_prefix in ma_prefixes:
        is_long: int = int(row["is_long"])
        is_ma_green_candle: int = int(row[f"is_{ma_prefix}_green_candle"])

        if is_long and is_ma_green_candle and row[f"streak_is_{ma_prefix}_green_candle"] > 1:
            for potential_column in potential_columns:
                if ma_prefix in potential_column and row[potential_column] < _POTENTIAL_THRESHOLD:
                    matching_columns.append(potential_column)
        if not is_long and not is_ma_green_candle and row[f"streak_is_{ma_prefix}_green_candle"] > 1:
            for potential_column in potential_columns:  # noqa: WPS440
                if ma_prefix in potential_column and row[potential_column] < _POTENTIAL_THRESHOLD:
                    matching_columns.append(potential_column)
    return sorted(set(matching_columns))


# pylint: enable=too-complex


def set_market_regime(delta: float | None) -> int | None:
    market_regime: int | None = None
    if not delta:
        return market_regime
    market_regime = int(floor(delta) * 10)
    return market_regime


# pylint: disable=too-many-locals, too-many-statements, disallowed-name
def quantile_matching_fit(row: dict[str, float], target_column: str, matching_columns: list[str]) -> float | None:
    mean: float = row["matching_mean"]  # TODO: ...

    fit: float | None = None
    if not matching_columns:
        return fit
    n: int = len(matching_columns)  # noqa: WPS111
    if n == 1:
        fit = row[matching_columns[0]]
        return fit

    for first, second in combinations(iterable=matching_columns, r=2):
        matching_columns.append(f"mean_horizontal_{first}_{second}")
    matching_columns.append("matching_mean")
    matching_columns.append("matching_minmax_mean")

    matching_columns = sorted(set(matching_columns))

    values: ndarray = array([row[matching_column] for matching_column in matching_columns])
    target: float = row[target_column]
    diff: ndarray = abs(target - values)

    best_fit: float = row[matching_columns[argmin(diff)]]
    best_fit_diff: float = min(diff)
    best_fit = (best_fit + mean) / 2  # TODO: ...

    n = len(matching_columns)  # noqa: WPS111
    k: int = numpy_sum(diff == best_fit_diff)  # noqa: WPS111
    best_fit_weight: float = _RANK_WEIGHT + ((1 - _RANK_WEIGHT) * (1 / (n - (k - 1))))
    if k > 1:
        best_fit_weight = best_fit_weight / k  # noqa: WPS350

    best_mask = diff == best_fit_diff
    non_best_mask = diff > best_fit_diff

    weights: ndarray = zeros(n)
    weights[best_mask] = best_fit_weight

    remaining_weight: float = 1 - best_fit_weight * k
    if remaining_weight > 0 and numpy_any(non_best_mask):
        non_best_diff: ndarray = abs(values[non_best_mask] - best_fit)

        inverse_weights: ndarray = 1 / non_best_diff
        inverse_weights = inverse_weights / numpy_sum(inverse_weights) * remaining_weight

        weights[non_best_mask] = inverse_weights
    fit = float(numpy_sum(weights * values))
    return fit


# pylint: enable=too-many-locals, too-many-statements, disallowed-name


def matching_min(row: dict[str, float], matching_columns: list[str]) -> float | None:
    minmax: float | None = None
    if not matching_columns:
        return minmax
    values: list[float] = [row[matching_column] for matching_column in matching_columns]
    minmax = min(values)
    return minmax


def matching_max(row: dict[str, float], matching_columns: list[str]) -> float | None:
    minmax: float | None = None
    if not matching_columns:
        return minmax
    values: list[float] = [row[matching_column] for matching_column in matching_columns]
    minmax = max(values)
    return minmax


def matching_mean(row: dict[str, float], matching_columns: list[str]) -> float | None:
    mean: float | None = None
    if not matching_columns:
        return mean

    matching_length: int = len(matching_columns)

    total_sum: float = 0
    for matching_column in matching_columns:  # noqa: WPS519
        total_sum += float(row[matching_column])
    return total_sum / matching_length


def is_mean_horizontal_in_matching_columns(first: str, second: str, matching_columns: list[str]) -> int:
    is_in: int = 0
    if first in matching_columns and second in matching_columns:
        is_in = 1
    return is_in
