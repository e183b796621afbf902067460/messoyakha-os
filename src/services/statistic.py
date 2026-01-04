from itertools import combinations
from typing import Final

from numpy import any as numpy_any
from numpy import argmin, array, floor, ndarray
from numpy import sum as numpy_sum
from numpy import zeros

_POTENTIAL_THRESHOLD: Final[float] = 0.99  # TODO: ...


# pylint: disable=too-complex
def capture_matchings(  # noqa: WPS231
    row: dict[str, int | float], ma_prefixes: list[str], potentials: list[str]
) -> list[str]:
    matchings: list[str] = []
    for ma_prefix in ma_prefixes:
        is_long: int = int(row["is_long"])
        is_ma_green_candle: int = int(row[f"is_{ma_prefix}_green_candle"])

        if is_long and is_ma_green_candle and row[f"streak_is_{ma_prefix}_green_candle"] > 1:
            for potential in potentials:
                if ma_prefix in potential and row[potential] < _POTENTIAL_THRESHOLD:
                    matchings.append(potential)
        if not is_long and not is_ma_green_candle and row[f"streak_is_{ma_prefix}_green_candle"] > 1:
            for potential in potentials:  # noqa: WPS440
                if ma_prefix in potential and row[potential] < _POTENTIAL_THRESHOLD:
                    matchings.append(potential)
    return sorted(set(matchings))


# pylint: enable=too-complex


def set_confidence_degree(delta: float | None) -> int | None:
    confidence_degree: int | None = None
    if not delta:
        return confidence_degree
    confidence_degree = int(floor(delta) * 10)
    return confidence_degree


# pylint: disable=too-many-locals, too-many-statements, disallowed-name
def quantile_matching_fit(row: dict[str, float], target: str, indicator: str, matchings: list[str]) -> float | None:
    fit: float | None = None
    if not matchings:
        return fit
    n: int = len(matchings)  # noqa: WPS111
    if n == 1:
        fit = row[matchings[0]]
        return fit
    max_weight_per_matching: float = 1 / n

    for first, second in combinations(iterable=matchings, r=2):
        matchings.append(f"mean_horizontal_{first}_{second}")
    matchings.append(f"mean_{indicator}_matchings")
    matchings.append(f"mean_{indicator}_minmax_matchings")

    matchings = sorted(set(matchings))

    values: ndarray = array([row[matching] for matching in matchings])
    diff: ndarray = abs(row[target] - values)

    best_fit: float = row[matchings[argmin(diff)]]
    best_fit_diff: float = min(diff)

    n = len(matchings)  # noqa: WPS111
    k: int = numpy_sum(diff == best_fit_diff)  # noqa: WPS111

    best_fit_weight: float = max_weight_per_matching + ((1 - max_weight_per_matching) * (1 / (n - (k - 1))))
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


def min_by_matchings(row: dict[str, float], matchings: list[str]) -> float | None:
    minmax: float | None = None
    if not matchings:
        return minmax
    values: list[float] = [row[matching_column] for matching_column in matchings]
    minmax = min(values)
    return minmax


def max_by_matchings(row: dict[str, float], matchings: list[str]) -> float | None:
    minmax: float | None = None
    if not matchings:
        return minmax
    values: list[float] = [row[matching_column] for matching_column in matchings]
    minmax = max(values)
    return minmax


def mean_by_matchings(row: dict[str, float], matchings: list[str]) -> float | None:
    mean: float | None = None
    if not matchings:
        return mean

    matching_length: int = len(matchings)

    total_sum: float = 0
    for matching_column in matchings:  # noqa: WPS519
        total_sum += float(row[matching_column])
    return total_sum / matching_length


def is_mean_horizontal_in_matchings(first: str, second: str, matchings: list[str]) -> int:
    is_in: int = 0
    if first in matchings and second in matchings:
        is_in = 1
    return is_in
