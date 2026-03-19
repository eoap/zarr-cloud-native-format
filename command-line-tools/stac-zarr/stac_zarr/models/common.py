from pydantic import BaseModel, ConfigDict


def is_none(value: object) -> bool:
    return value is None


class ZarrConventionMetadata(BaseModel):
    uuid: str
    name: str
    schema_url: str
    spec_url: str
    description: str

    model_config = ConfigDict(extra="forbid")
