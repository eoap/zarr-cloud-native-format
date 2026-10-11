"""Shared schema restoration must preserve module-owned definitions."""

from shared_schema_imports import restore_published_schemas


def test_remote_types_are_imported_once_and_local_types_stay_inline():
    remote = "https://raw.githubusercontent.com/eoap/schemas/main/string_format.yaml"
    local = {"name": "Measurement", "type": "enum", "symbols": ["water", "ndwi"]}
    document = {
        "requirements": [
            {
                "class": "SchemaDefRequirement",
                "types": [
                    {"name": remote + "#URI", "type": "record", "fields": []},
                    {"name": remote + "#DateTime", "type": "record", "fields": []},
                    local,
                ],
            }
        ]
    }
    restore_published_schemas(document)
    assert document["requirements"][0]["types"] == [{"$import": remote}, local]


def test_existing_imports_are_preserved():
    document = {
        "types": [{"$import": "https://raw.githubusercontent.com/eoap/schemas/main/ogc.yaml"}]
    }
    previous = list(document["types"])
    restore_published_schemas(document)
    assert document["types"] == previous
