from pydantic import BaseModel, ConfigDict


class GeoZarrBaseModel(BaseModel):
    """Shared base for generated convention models."""

    model_config = ConfigDict(extra="allow", populate_by_name=True, serialize_by_alias=True)
