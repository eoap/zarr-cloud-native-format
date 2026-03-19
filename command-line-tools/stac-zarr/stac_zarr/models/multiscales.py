from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TileMatrix(BaseModel):
    id: str
    scale_denominator: float = Field(alias="scaleDenominator")
    cell_size: float = Field(alias="cellSize")
    point_of_origin: list[float] = Field(alias="pointOfOrigin")
    tile_width: int = Field(alias="tileWidth")
    tile_height: int = Field(alias="tileHeight")
    matrix_width: int = Field(alias="matrixWidth")
    matrix_height: int = Field(alias="matrixHeight")

    model_config = ConfigDict(extra="forbid", populate_by_name=True, serialize_by_alias=True)

    @model_validator(mode="after")
    def validate_positive(self) -> "TileMatrix":
        if self.tile_width <= 0 or self.tile_height <= 0:
            raise ValueError("tileWidth and tileHeight must be > 0")
        if self.matrix_width <= 0 or self.matrix_height <= 0:
            raise ValueError("matrixWidth and matrixHeight must be > 0")
        return self


class TileMatrixSet(BaseModel):
    id: str
    title: str
    crs: str
    ordered_axes: list[str] = Field(alias="orderedAxes")
    tile_matrices: list[TileMatrix] = Field(alias="tileMatrices")

    model_config = ConfigDict(extra="forbid", populate_by_name=True, serialize_by_alias=True)


class Multiscales(BaseModel):
    resampling_method: Literal["nearest", "average", "max", "med"] = Field(alias="resampling_method")
    tile_matrix_set: TileMatrixSet = Field(alias="tile_matrix_set")

    model_config = ConfigDict(extra="forbid", populate_by_name=True, serialize_by_alias=True)


class Axis(BaseModel):
    name: str
    type: Literal["temporal", "spatial"]

    model_config = ConfigDict(extra="forbid")


class MultiscaleDataset(BaseModel):
    path: str
    level: int | None = None
    spatial_shape: list[int] | None = Field(None, alias="spatial:shape")
    spatial_transform: list[float] | None = Field(None, alias="spatial:transform")
    downsampling_factor: int | None = None
    overview_reducer: str | None = Field(None, alias="overview:reducer")
    overview_variable_type: str | None = Field(None, alias="overview:variable_type")

    model_config = ConfigDict(extra="allow", populate_by_name=True, serialize_by_alias=True)


class MultiscalesDatasetEntry(BaseModel):
    name: str
    datasets: list[MultiscaleDataset]
    axes: list[Axis]

    model_config = ConfigDict(extra="forbid")
