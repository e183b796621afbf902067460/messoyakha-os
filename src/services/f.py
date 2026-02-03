from itertools import combinations
from typing import Final
from random import choice

from pandas import DataFrame
from polars import DataFrame as PolarsDF
from polars import all as all_columns
from polars import mean_horizontal, struct, col
from loguru import logger

from src.services.statistics import (
    af,
    capture_matchings,
    is_mean_horizontal_in_matchings,
    median_by_matchings,
    median_high_spread_by_matchings,
    median_low_spread_by_matchings,
    quantile_by_matchings,
)


_LOWEST_QUANTILE: Final[float] = 0.2
_LOWEST_HALF_QUANTILE: Final[float] = 0.35
_HIGHEST_HALF_QUANTILE: Final[float] = 0.65
_HIGHEST_QUANTILE: Final[float] = 0.8


def r(
    data: DataFrame,
    ma_prefixes: list[str],
    adx_columns: list[str],
) -> float | None:
    data = PolarsDF(data=data)

    data = data.with_columns(
        struct(all_columns())  # noqa: WPS204
        .map_elements(
            function=lambda row: capture_matchings(
                row=row,
                ma_prefixes=ma_prefixes,
                potentials=adx_columns,
            )
        )
        .alias(name="adx_matchings")
    )
    matchings: list[str] = data.item(0, "adx_matchings").to_list()
    if matchings:
        return data.item(0, choice(seq=matchings))
    return None


def f(
    data: DataFrame,
    ma_prefixes: list[str],
    adx_columns: list[str], categorical_columns: list[str],
    *,
    is_logs: bool = False
) -> DataFrame | None:
    data = PolarsDF(data=data)

    # TODO: r=3, r=4 etc. and add them to QMF-function
    for first, second in combinations(iterable=adx_columns, r=2):
        data = data.with_columns(mean_horizontal(first, second).alias(name=f"mean_horizontal_{first}_{second}"))
    data = data.with_columns(
        struct(all_columns())  # noqa: WPS204
        .map_elements(
            function=lambda row: capture_matchings(
                row=row,
                ma_prefixes=ma_prefixes,
                potentials=adx_columns,
            )
        )
        .alias(name="adx_matchings")
    )
    data = data.with_columns(length_adx_matchings=col("adx_matchings").list.len())
    data = data.filter((col("length_adx_matchings") > 1))
    if data.shape[0] < 1:
        return None

    data = data.with_columns(
        struct(all_columns())
        .map_elements(
            function=lambda row: quantile_by_matchings(
                row=row, matchings=row["adx_matchings"], q=_LOWEST_QUANTILE  # noqa: WPS204
            )
        )
        .alias(name="quantile_adx_matchings_low")
    )
    data = data.with_columns(
        struct(all_columns())
        .map_elements(
            function=lambda row: quantile_by_matchings(row=row, matchings=row["adx_matchings"], q=_LOWEST_HALF_QUANTILE)
        )
        .alias(name="quantile_adx_matchings_half_low")
    )
    data = data.with_columns(
        struct(all_columns())
        .map_elements(function=lambda row: median_by_matchings(row=row, matchings=row["adx_matchings"]))
        .alias(name="median_adx_matchings")
    )
    data = data.with_columns(
        struct(all_columns())
        .map_elements(
            function=lambda row: quantile_by_matchings(
                row=row, matchings=row["adx_matchings"], q=_HIGHEST_HALF_QUANTILE
            )
        )
        .alias(name="quantile_adx_matchings_half_high")
    )
    data = data.with_columns(
        struct(all_columns())
        .map_elements(
            function=lambda row: quantile_by_matchings(row=row, matchings=row["adx_matchings"], q=_HIGHEST_QUANTILE)
        )
        .alias(name="quantile_adx_matchings_high")
    )
    data = data.with_columns(
        delta_adx_quantile_matchings=col("quantile_adx_matchings_high") - col("quantile_adx_matchings_low")
    )
    data = data.with_columns(
        scaled_delta_adx_quantile_matchings=col("delta_adx_quantile_matchings") / col("length_adx_matchings")
    )

    for adx_column in adx_columns + [  # noqa: WPS426
        "quantile_adx_matchings_low",
        "quantile_adx_matchings_half_low",
        "median_adx_matchings",
        "quantile_adx_matchings_half_high",
        "quantile_adx_matchings_high",
    ]:
        data = data.with_columns(
            col("adx_matchings").list.contains(item=adx_column).alias(name=f"is_{adx_column}_in_matchings")
        )
        data = data.with_columns(
            struct(all_columns())
            .map_elements(
                function=lambda row: af(row=row, assume=adx_column, indicator="adx", matchings=row["adx_matchings"])
            )
            .alias(name=f"assume_{adx_column}_is_target")
        )
        data = data.with_columns(
            struct(all_columns())
            .map_elements(
                function=lambda row: af(
                    row=row, assume=adx_column, indicator="adx", matchings=row["adx_matchings"], is_reversed=True
                )
            )
            .alias(name=f"reversed_assume_{adx_column}_is_target")
        )
    for first, second in combinations(iterable=adx_columns, r=2):  # noqa: WPS426 WPS440
        data = data.with_columns(
            struct(all_columns())
            .map_elements(
                function=lambda row: is_mean_horizontal_in_matchings(
                    first=first, second=second, matchings=row["adx_matchings"]
                )
            )
            .alias(name=f"is_mean_horizontal_{first}_{second}_in_matchings")
        )
        data = data.with_columns(
            struct(all_columns())
            .map_elements(
                function=lambda row: af(
                    row=row, assume=f"mean_horizontal_{first}_{second}", indicator="adx", matchings=row["adx_matchings"]
                )
            )
            .alias(name=f"assume_mean_horizontal_{first}_{second}_is_target")
        )
        data = data.with_columns(
            struct(all_columns())
            .map_elements(
                function=lambda row: af(
                    row=row,
                    assume=f"mean_horizontal_{first}_{second}",
                    indicator="adx",
                    matchings=row["adx_matchings"],
                    is_reversed=True,
                )
            )
            .alias(name=f"reversed_assume_mean_horizontal_{first}_{second}_is_target")
        )
    assume_adx_columns: list[str] = [column for column in data.columns if column.startswith("assume")]
    if is_logs:
        logger.info("Booleans and assumes computed.")

    # TODO: [assume_adx_columns, reversed_assume_adx_columns]
    data = data.with_columns(
        struct(all_columns())
        .map_elements(
            function=lambda row: quantile_by_matchings(
                row=row, matchings=assume_adx_columns, q=_LOWEST_QUANTILE, is_assume=True
            )
        )
        .alias(name="quantile_assume_adx_matchings_low")
    )
    data = data.with_columns(
        struct(all_columns())
        .map_elements(
            function=lambda row: quantile_by_matchings(
                row=row, matchings=assume_adx_columns, q=_LOWEST_HALF_QUANTILE, is_assume=True
            )
        )
        .alias(name="quantile_assume_adx_matchings_half_low")
    )
    data = data.with_columns(
        struct(all_columns())
        .map_elements(function=lambda row: median_by_matchings(row=row, matchings=assume_adx_columns, is_assume=True))
        .alias(name="median_assume_adx_matchings")
    )
    data = data.with_columns(
        struct(all_columns())
        .map_elements(
            function=lambda row: quantile_by_matchings(
                row=row, matchings=assume_adx_columns, q=_HIGHEST_HALF_QUANTILE, is_assume=True
            )
        )
        .alias(name="quantile_assume_adx_matchings_half_high")
    )
    data = data.with_columns(
        struct(all_columns())
        .map_elements(
            function=lambda row: quantile_by_matchings(
                row=row, matchings=assume_adx_columns, q=_HIGHEST_QUANTILE, is_assume=True
            )
        )
        .alias(name="quantile_assume_adx_matchings_high")
    )
    data = data.with_columns(
        delta_quantile_adx_quantile_matchings=(
                col("quantile_assume_adx_matchings_high") - col("quantile_assume_adx_matchings_low")
        )
    )
    data = data.with_columns(
        scaled_delta_quantile_adx_quantile_matchings=(
                col("delta_quantile_adx_quantile_matchings") / col("length_adx_matchings")
        )
    )
    if is_logs:
        logger.info("Quantile assumes computed.")

    data = data.with_columns(
        struct(all_columns())
        .map_elements(
            function=lambda row: median_low_spread_by_matchings(row=row, matchings=assume_adx_columns, indicator="adx")
        )
        .alias(name="spread_low_adx_matchings")
    )
    data = data.with_columns(
        struct(all_columns())
        .map_elements(
            function=lambda row: median_high_spread_by_matchings(row=row, matchings=assume_adx_columns, indicator="adx")
        )
        .alias(name="spread_high_adx_matchings")
    )

    data = data.to_pandas()
    for categorical_feature in categorical_columns:
        data[categorical_feature] = data[categorical_feature].astype(int)
    return data
