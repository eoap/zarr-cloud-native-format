from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal

import pystac
from pystac.extensions.base import PropertiesExtension, ExtensionManagementMixin
from pystac.utils import get_required, map_opt

CF_SCHEMA_URI: str = "https://stac-extensions.github.io/cf/v0.2.0/schema.json"
CF_PREFIX: str = "cf:"
CF_PARAMETER_PROP: str = CF_PREFIX + "parameter"


class CfParameter:
    """Wrapper for a single entry in cf:parameter."""

    def __init__(self, properties: Dict[str, Any]):
        self.properties = properties

    @property
    def name(self) -> str:
        return get_required(self.properties.get("name"), self, "name")

    @name.setter
    def name(self, v: str) -> None:
        self.properties["name"] = v

    @property
    def unit(self) -> Optional[str]:
        return self.properties.get("unit")

    @unit.setter
    def unit(self, v: Optional[str]) -> None:
        if v is None:
            self.properties.pop("unit", None)
        else:
            self.properties["unit"] = v

    @classmethod
    def create(cls, name: str, unit: Optional[str] = None) -> "CfParameter":
        p = cls({})
        p.name = name
        if unit is not None:
            p.unit = unit
        return p

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.properties)


class _CfCommon(PropertiesExtension):
    """Shared implementation of cf:parameter for Item and Asset extensions."""

    @property
    def parameters(self) -> Optional[List[CfParameter]]:
        """List of CfParameter or None if not set."""
        raw = self._get_property(CF_PARAMETER_PROP, List[Dict[str, Any]])
        return map_opt(lambda arr: [CfParameter(d) for d in arr], raw)

    @parameters.setter
    def parameters(self, v: Optional[List[CfParameter]]) -> None:
        self._set_property(
            CF_PARAMETER_PROP,
            map_opt(lambda arr: [p.to_dict() for p in arr], v),
            pop_if_none=True,
        )


class ItemCfExtension(_CfCommon, ExtensionManagementMixin[pystac.Item]):
    """CF extension for pystac.Item (cf:parameter in item.properties)."""

    # Optional: lets you later plug into Item.ext if you want
    name: Literal["cf"] = "cf"

    def __init__(self, item: pystac.Item):
        self.item = item
        self.properties = item.properties

    @classmethod
    def get_schema_uri(cls) -> str:
        return CF_SCHEMA_URI

    @classmethod
    def ext(
        cls,
        obj: pystac.Item,
        add_if_missing: bool = False,
    ) -> "ItemCfExtension":
        if not isinstance(obj, pystac.Item):
            raise pystac.ExtensionTypeError(
                f"ItemCfExtension does not apply to type '{type(obj).__name__}'"
            )
        cls.ensure_has_extension(obj, add_if_missing=add_if_missing)
        return cls(obj)
