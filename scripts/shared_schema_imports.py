"""Restore published EOAP schema imports expanded by the CWL SDK serializer."""

PUBLISHED_SCHEMA_ROOT = "https://raw.githubusercontent.com/eoap/schemas/"


def restore_published_schemas(value: object) -> None:
    """Keep shared types as imports while retaining inline module-owned types."""
    if isinstance(value, list):
        for item in value:
            restore_published_schemas(item)
    elif isinstance(value, dict):
        types = value.get("types")
        if isinstance(types, list):
            imports: set[str] = set()
            restored: list[object] = []
            for schema in types:
                name = schema.get("name") if isinstance(schema, dict) else None
                if isinstance(name, str) and name.startswith(PUBLISHED_SCHEMA_ROOT):
                    location, fragment = name.split("#", 1) if "#" in name else (name, "")
                    if fragment and location.endswith(".yaml"):
                        if location not in imports:
                            restored.append({"$import": location})
                            imports.add(location)
                        continue
                restored.append(schema)
            value["types"] = restored
        for item in value.values():
            restore_published_schemas(item)
