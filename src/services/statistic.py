from numpy import argmin, array, exp, ndarray
from pandas import DataFrame, Series

# TODO: simple multiplier means and weighted multiplier means


def _identify_target(row: Series, matching_columns: list[str], target_column: str = "rank") -> str | None:
    for column in matching_columns:
        if row[target_column] == row[column]:
            return column
    return None


def determine_matching_columns(
    row: dict[str, int | float], ma_prefixes: list[str], potential_columns: list[str]
) -> list[str]:
    matching_columns: list[str] = []
    for ma_prefix in ma_prefixes:
        is_long: int = int(row["is_long"])
        is_ma_green_candle: int = int(row[f"is_{ma_prefix}_green_candle"])
        if is_long and is_ma_green_candle and row[f"streak_is_{ma_prefix}_green_candle"] > 1:
            matching_columns.extend(
                [potential_column for potential_column in potential_columns if ma_prefix in potential_column]
            )
        if not is_long and not is_ma_green_candle and row[f"streak_is_{ma_prefix}_green_candle"] > 1:
            matching_columns.extend(
                [potential_column for potential_column in potential_columns if ma_prefix in potential_column]
            )
    return sorted(set(matching_columns))


def quantile_matching_fit(row: dict[str, float], target_column: str, matching_columns: list[str]) -> float | None:
    fit: float | None = None
    if not matching_columns:
        return fit
    values: ndarray = array([row[matching_column] for matching_column in matching_columns])
    diff: ndarray = abs(row[target_column] - values)
    fit = row[matching_columns[argmin(diff)]]
    return fit


# pylint: disable=unused-argument


# TODO: ...
def compute_global_weights(data: DataFrame, matching_columns: list[str], target_column: str = "rank") -> dict[str, int]:
    global_weights: dict[str, int] = (
        data.apply(
            lambda row: _identify_target(
                row=row, matching_columns=row["matching_columns"], target_column=target_column
            ),
            axis=1,
        )
        .value_counts()
        .to_dict()
    )
    return global_weights


# TODO: ...
def compute_group_weights(
    data: DataFrame, grouping_column: str, matching_columns: list[str], target_column: str = "rank"
) -> dict[int, dict[str, int]]:
    data["_identified_rank"] = data.apply(
        lambda row: _identify_target(row=row, matching_columns=row["matching_columns"], target_column=target_column),
        axis=1,
    )
    data["mock"] = 1
    grouping: DataFrame = (
        data.groupby(by=[grouping_column, "_identified_rank"], as_index=False)
        .mock.count()
        .sort_values(by=[grouping_column, "mock"], ascending=[False, False])
    )
    group_weights: dict[int, dict[str, int]] = (
        grouping.groupby(grouping_column)
        .apply(lambda nest: nest.set_index("_identified_rank")["mock"].to_dict())
        .to_dict()
    )
    data.drop(columns=["_identified_rank", "mock"], inplace=True)
    return group_weights


# pylint: enable=unused-argument


def matching_mean(row: dict[str, float], matching_columns: list[str]) -> float | None:
    mean: float | None = None
    if not matching_columns:
        return mean

    matching_length: int = len(matching_columns)

    total_sum: int = 0
    for matching_column in matching_columns:  # noqa: WPS519
        total_sum += int(row[matching_column])
    return total_sum / matching_length


def matching_weighted_mean(
    row: dict[str, float], weights: dict[str, int], matching_columns: list[str], *, is_exp: bool = False
) -> float | None:
    weighted_mean: float | None = None
    if not matching_columns:
        return weighted_mean

    total_sum: int = 0
    weights_total_sum: int = 0
    for matching_column in matching_columns:
        weight: int = weights[matching_column] if matching_column in weights.keys() else 0
        weight = weight ** exp(2) if is_exp else weight
        total_sum += int(row[matching_column]) * weight
        weights_total_sum += weight
    weighted_mean = total_sum / weights_total_sum if weights_total_sum else weighted_mean
    return weighted_mean


def matching_mean_by_weights(
    row: dict[str, int | float],
    weights: dict[int, dict[str, int]],
    grouping_column: str,
    matching_columns: list[str],
) -> float | None:
    mean_by_weights: float | None = None
    if not matching_columns:
        return mean_by_weights
    weight_key: int = int(row[grouping_column])
    if weight_key not in weights.keys():
        return mean_by_weights
    filtered_weights: dict[str, int] = {key: value for key, value in weights[weight_key].items() if value != 0}
    if not filtered_weights:
        return mean_by_weights

    total_sum: float = 0
    total_weights_sum: int = 0
    for matching_column in matching_columns:
        if matching_column in filtered_weights.keys():
            total_sum += row[matching_column]
            total_weights_sum += 1
    mean_by_weights = total_sum / total_weights_sum if total_weights_sum else mean_by_weights
    return mean_by_weights


# pylint: disable=too-many-locals
def matching_weighted_mean_by_weights(
    row: dict[str, int | float],
    weights: dict[int, dict[str, int]],
    grouping_column: str,
    matching_columns: list[str],
    *,
    is_exp: bool = False,
) -> float | None:
    weighted_mean_by_weights: float | None = None
    if not matching_columns:
        return weighted_mean_by_weights
    weight_key: int = int(row[grouping_column])
    if weight_key not in weights.keys():
        return weighted_mean_by_weights
    filtered_weights: dict[str, int] = {key: value for key, value in weights[weight_key].items() if value != 0}
    if not filtered_weights:
        return weighted_mean_by_weights

    total_sum: float = 0
    total_weights_sum: int = 0
    for matching_column in matching_columns:
        if matching_column in filtered_weights.keys():
            weight = filtered_weights[matching_column] ** exp(2) if is_exp else filtered_weights[matching_column]
            total_sum += row[matching_column] * weight
            total_weights_sum += weight
    weighted_mean_by_weights = total_sum / total_weights_sum if total_weights_sum else weighted_mean_by_weights
    return weighted_mean_by_weights


# pylint: enable=too-many-locals
