from attr import attrs
from pandas import DataFrame, Series


def _identify_target(row: Series, columns: list[str], target: str = "rank") -> str | None:
    for quantile_column in columns:
        if row[target] == row[quantile_column]:
            return quantile_column
    return None


@attrs(slots=True, auto_attribs=True, kw_only=True)
class TargetEngineeringService:

    target_data: DataFrame
    target_columns: list[str]

    @property
    def weights(self) -> dict[str, float]:
        return (  # type: ignore[no-any-return]
            self.target_data.apply(lambda row: _identify_target(row=row, columns=self.target_columns), axis=1)
            .value_counts()
            .to_dict()
        )

    @property
    def multipliers(self) -> list[int]:
        return [multiplier for multiplier in range(2, len(self.target_columns) + 1) if multiplier % 2 == 0]
