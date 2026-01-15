# pylint: disable=too-many-lines
from itertools import combinations

from numpy import mean, median, quantile


# pylint: disable=too-complex
def capture_matchings(  # noqa: WPS231
    row: dict[str, int | float], ma_prefixes: list[str] | None, potentials: list[str]
) -> list[str]:
    matchings: list[str] = []
    if not ma_prefixes:
        return matchings

    for ma_prefix in ma_prefixes:
        is_long: int = int(row["is_long"])
        is_ma_green_candle: int = int(row[f"is_{ma_prefix}_green_candle"])

        if is_long and is_ma_green_candle and row[f"streak_is_{ma_prefix}_green_candle"] > 1:
            for potential in potentials:
                if ma_prefix in potential:
                    matchings.append(potential)
        if not is_long and not is_ma_green_candle and row[f"streak_is_{ma_prefix}_green_candle"] > 1:
            for potential in potentials:  # noqa: WPS440
                if ma_prefix in potential:
                    matchings.append(potential)
    return sorted(set(matchings))


# pylint: disable=too-many-locals, too-many-statements, disallowed-name, invalid-name, too-many-branches
def qmf(row: dict[str, float], target: str, indicator: str, matchings: list[str]) -> float | None:  # noqa: WPS231
    fit: float | None = None
    if not matchings:  # noqa: WPS204
        return fit
    n: int = len(matchings)  # noqa: WPS111
    if n == 1:
        fit = row[matchings[0]]
        return fit

    for first, second in combinations(iterable=matchings, r=2):
        matchings.append(f"mean_horizontal_{first}_{second}")
    matchings.append(f"quantile_{indicator}_matchings_low")
    matchings.append(f"quantile_{indicator}_matchings_half_low")
    matchings.append(f"median_{indicator}_matchings")
    matchings.append(f"quantile_{indicator}_matchings_half_high")
    matchings.append(f"quantile_{indicator}_matchings_high")

    matchings = sorted(set(matchings))

    low_quantile: float = row[f"quantile_{indicator}_matchings_low"]
    low_half_quantile: float = row[f"quantile_{indicator}_matchings_half_low"]
    median_quantile: float = row[f"median_{indicator}_matchings"]
    high_half_quantile: float = row[f"quantile_{indicator}_matchings_half_high"]
    high_quantile: float = row[f"quantile_{indicator}_matchings_high"]

    values: list[float] = []
    valid_matchings: list[str] = []
    for matching in matchings:
        match: float = row[matching]  # noqa: WPS204
        if low_quantile <= match <= high_quantile and match not in values:
            values.append(match)
            valid_matchings.append(matching)

    if not values:
        return fit

    target_value = row[target]

    diff: list[float] = [target_value - value for value in values]
    absolute_diff: list[float] = [abs(diff_value) for diff_value in diff]
    absolute_median_diff: float = float(median(a=absolute_diff))

    best_fit_diff: float = min(absolute_diff)

    low_half_quantile_diff: float = target_value - low_half_quantile
    median_fit_diff: float = target_value - median_quantile
    high_half_quantile_diff: float = target_value - high_half_quantile

    best_fit_index: int = absolute_diff.index(best_fit_diff)
    best_fit_indicator: str = valid_matchings[best_fit_index]
    best_fit_value: float = row[best_fit_indicator]

    if abs(median_fit_diff) < absolute_median_diff:
        max_weight_best_fit: float = 1 - 1 / n

        fits: list[float] = (
            [abs(low_half_quantile_diff), abs(median_fit_diff)]
            if median_fit_diff < 0
            else [abs(high_half_quantile_diff), abs(median_fit_diff)]
        )
        best_fit_diff = min(fits)
        poor_fit_diff: float = max(fits)

        best_fit_index = absolute_diff.index(best_fit_diff)
        poor_fit_index: int = absolute_diff.index(poor_fit_diff)

        best_fit_indicator = valid_matchings[best_fit_index]
        poor_fit_indicator: str = valid_matchings[poor_fit_index]

        best_fit_value = (
            row[best_fit_indicator]
            if row[best_fit_indicator] == median_quantile
            else row[best_fit_indicator] * max_weight_best_fit + row[poor_fit_indicator] * (1 - max_weight_best_fit)
        )
    else:
        max_weight_best_fit = 1 / n * (1 - (high_quantile - low_quantile))

    k: int = max(absolute_diff.count(best_fit_diff), 1)  # noqa: WPS111

    best_fit_weight: float = (
        max_weight_best_fit + ((1 - max_weight_best_fit) * (1 / (len(values) - (k - 1))))
        if k > 1
        else max_weight_best_fit
    )
    if k > 1:
        max_weight_best_fit = best_fit_weight / k  # noqa: WPS350

    weights: list[float] = [0.0] * len(values)  # noqa: WPS435
    for index, diff_value in enumerate(absolute_diff):
        if diff_value == best_fit_diff:
            weights[index] = max_weight_best_fit

    remaining_weight: float = 1 - max_weight_best_fit * k
    if remaining_weight > 0:
        non_best_indices = [
            index for index, diff_value in enumerate(absolute_diff) if diff_value > best_fit_diff  # noqa: WPS441
        ]
        if non_best_indices:
            non_best_values = [values[index] for index in non_best_indices]  # noqa: WPS441
            non_best_diff_values = [abs(non_best_value - best_fit_value) for non_best_value in non_best_values]

            inverse_weights = [1 / non_best_diff_value for non_best_diff_value in non_best_diff_values]
            sum_inverse_weights = sum(inverse_weights)
            normalized_weights = [weight / sum_inverse_weights * remaining_weight for weight in inverse_weights]

            for index, weight in zip(non_best_indices, normalized_weights, strict=True):  # noqa: WPS440
                weights[index] = weight

    fit = float(sum(weight * value for weight, value in zip(weights, values, strict=True)))  # noqa: WPS441
    return fit


def af(  # noqa: WPS231
    row: dict[str, float], assume: str, indicator: str, matchings: list[str], *, is_reversed: bool = False
) -> float | None:
    fit: float | None = None
    if not matchings:
        return fit
    n: int = len(matchings)  # noqa: WPS111
    if n == 1:
        fit = row[matchings[0]]
        return fit
    max_weight_best_fit: float = 1 / n

    for first, second in combinations(iterable=matchings, r=2):
        matchings.append(f"mean_horizontal_{first}_{second}")
    matchings.append(f"quantile_{indicator}_matchings_low")
    matchings.append(f"quantile_{indicator}_matchings_half_low")
    matchings.append(f"median_{indicator}_matchings")
    matchings.append(f"quantile_{indicator}_matchings_half_high")
    matchings.append(f"quantile_{indicator}_matchings_high")

    matchings = sorted(set(matchings))

    low: float = row[f"quantile_{indicator}_matchings_low"]
    high: float = row[f"quantile_{indicator}_matchings_high"]

    values: list[float] = []
    valid_matchings: list[str] = []
    for matching in matchings:
        match: float = row[matching]
        if low <= match <= high:
            values.append(match)
            valid_matchings.append(matching)

    if not values:
        return fit

    nearest: float = (
        row[assume]
        if assume in matchings
        else row[valid_matchings[min(range(len(values)), key=lambda index: abs(row[assume] - values[index]))]]
    )
    diff: list[float] = [abs(nearest - value) for value in values]

    k: int = diff.count(0)  # noqa: WPS111

    best_fit_weight: float = max_weight_best_fit + ((1 - max_weight_best_fit) * (1 / (len(values) - (k - 1))))
    if k > 1:
        best_fit_weight = best_fit_weight / k  # noqa: WPS350

    weights: list[float] = [0.0] * len(values)  # noqa: WPS435
    for index, diff_value in enumerate(diff):  # noqa: WPS440
        if diff_value == 0:
            weights[index] = best_fit_weight

    remaining_weight: float = 1 - best_fit_weight * k
    if remaining_weight > 0:
        non_zero_indices = [index for index, diff_value in enumerate(diff) if diff_value > 0]  # noqa: WPS441
        if non_zero_indices:
            non_zero_values = [values[index] for index in non_zero_indices]  # noqa: WPS441
            non_zero_diff = [abs(non_zero_value - nearest) for non_zero_value in non_zero_values]

            # TODO: add mode where error made above/below while median > (<) 0.5 are higher/lower than otherwise
            inverse_weights = (
                non_zero_diff if is_reversed else [1 / diff_value for diff_value in non_zero_diff]  # noqa: WPS441
            )
            sum_inverse_weights = sum(inverse_weights)
            normalized_weights = [
                inverse_weight / sum_inverse_weights * remaining_weight for inverse_weight in inverse_weights
            ]
            for index, weight in zip(non_zero_indices, normalized_weights, strict=True):  # noqa: WPS440
                weights[index] = weight
    fit = float(sum(weight * value for weight, value in zip(weights, values, strict=True)))  # noqa: WPS441
    return fit


# pylint: enable=too-many-locals, too-many-statements, too-complex, invalid-name


def percents_separated(row: dict[str, float], separator: float, indicator: str, matchings: list[str]) -> float | None:
    percents: float | None = None
    if not matchings:
        return percents
    for first, second in combinations(iterable=matchings, r=2):
        matchings.append(f"mean_horizontal_{first}_{second}")
    matchings.append(f"median_{indicator}_matchings")

    matchings = sorted(set(matchings))
    n: int = len(matchings)  # noqa: WPS111

    separated_count: int = 0
    for matching in matchings:
        if row[matching] > separator:
            separated_count += 1
    percents = separated_count / n
    return percents


# pylint: enable=disallowed-name


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
    fit: float | None = None
    if not matchings:
        return fit

    values: list[float] = [float(row[matching]) for matching in matchings]
    fit = float(mean(a=values))
    return fit


def median_low_spread_by_matchings(row: dict[str, float], matchings: list[str], indicator: str) -> float | None:
    fit: float | None = None
    if not matchings:
        return fit

    values: list[float] = [
        float(row[matching]) - row[f"quantile_assume_{indicator}_matchings_low"] for matching in matchings
    ]
    values = sorted(set(values))
    fit = float(median(a=values))
    return fit


def median_high_spread_by_matchings(row: dict[str, float], matchings: list[str], indicator: str) -> float | None:
    fit: float | None = None
    if not matchings:
        return fit

    values: list[float] = [
        float(row[matching]) - row[f"quantile_assume_{indicator}_matchings_high"] for matching in matchings
    ]
    values = sorted(set(values))
    fit = float(median(a=values))
    return fit


def median_by_matchings(row: dict[str, float], matchings: list[str], *, is_assume: bool = False) -> float | None:
    fit: float | None = None
    if not matchings:
        return fit
    if not is_assume:
        for first, second in combinations(iterable=matchings, r=2):
            matchings.append(f"mean_horizontal_{first}_{second}")

    values: list[float] = [float(row[matching]) for matching in matchings]
    values = sorted(set(values))
    fit = float(median(a=values))
    return fit


# pylint: disable=invalid-name
def quantile_by_matchings(
    row: dict[str, float], matchings: list[str], q: float = 0.5, *, is_assume: bool = False  # noqa: WPS111
) -> float | None:
    fit: float | None = None
    if not matchings:
        return fit
    if not is_assume:
        for first, second in combinations(iterable=matchings, r=2):
            matchings.append(f"mean_horizontal_{first}_{second}")

    values: list[float] = [float(row[matching]) for matching in matchings]
    values = sorted(set(values))
    fit = float(quantile(a=values, q=q))
    return fit


# pylint: enable=invalid-name


def is_mean_horizontal_in_matchings(first: str, second: str, matchings: list[str]) -> int:
    is_in: int = 0
    if first in matchings and second in matchings:
        is_in = 1
    return is_in
