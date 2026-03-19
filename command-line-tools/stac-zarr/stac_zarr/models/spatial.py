from pydantic import BaseModel, ConfigDict, Field, model_validator

from stac_zarr.models.common import is_none


class Spatial(BaseModel):
    dimensions: list[str] = Field(alias="spatial:dimensions")
    bbox: list[float] | None = Field(None, alias="spatial:bbox", exclude_if=is_none)
    transform_type: str = Field("affine", alias="spatial:transform_type")
    transform: list[float] | None = Field(None, alias="spatial:transform", exclude_if=is_none)
    shape: list[int] | None = Field(None, alias="spatial:shape", exclude_if=is_none)
    registration: str = Field("pixel", alias="spatial:registration")

    model_config = ConfigDict(extra="allow", populate_by_name=True, serialize_by_alias=True)

    @model_validator(mode="after")
    def validate_dimensions_not_empty(self) -> "Spatial":
        if not self.dimensions:
            raise ValueError("spatial:dimensions must contain at least one dimension")
        return self
