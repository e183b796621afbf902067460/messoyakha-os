from pydantic import BaseModel, Field


class SARParametersSchema(BaseModel):

    start_value: float = Field(alias="startvalue")
    offset_on_reverse: float = Field(alias="offsetonreverse")

    acceleration_init_long: float = Field(alias="accelerationinitlong")
    acceleration_init_short: float = Field(alias="accelerationinitshort")

    acceleration_long: float = Field(alias="accelerationlong")
    acceleration_short: float = Field(alias="accelerationshort")

    acceleration_max_long: float = Field(alias="accelerationmaxlong")
    acceleration_max_short: float = Field(alias="accelerationmaxshort")
