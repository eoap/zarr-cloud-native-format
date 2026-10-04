"""TiTiler-EOPF dependency helpers with optional STAC API item resolution.

This module is designed to be copied into a TiTiler-EOPF codebase and used as
`path_dependency` in the factory. It keeps backward compatibility with the
current filesystem/object-store resolver while adding STAC API-backed lookup.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Annotated, Any, Dict, List, Literal
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from fastapi import Path, Query
from starlette.requests import Request as StarletteRequest

from titiler.core.dependencies import BidxParams, DefaultDependency, ExpressionParams
from titiler.xarray.dependencies import SelDimStr


@dataclass(frozen=True)
class ResolverSettings:
    """Resolver settings sourced from environment variables.

    Env vars:
    - TITILER_EOPF_STORE_URL: base URL for fallback path resolver.
      Example: file:///data/
    - TITILER_EOPF_STAC_API_URL: optional STAC API root URL.
      Example: https://example.com/stac
    - TITILER_EOPF_STAC_ASSET_KEY: item asset key to read Zarr href from.
      Default: measurements
    - TITILER_EOPF_STAC_TIMEOUT: HTTP timeout in seconds for STAC API calls.
      Default: 10
    - TITILER_EOPF_STAC_AUTH_TOKEN: optional bearer token for STAC API calls.
    - TITILER_EOPF_STAC_HEADERS_JSON: optional JSON object with extra headers.
      Example: {"x-api-key": "..."}
    """

    store_url: str = os.getenv("TITILER_EOPF_STORE_URL", "file:///data/")
    stac_api_url: str | None = os.getenv("TITILER_EOPF_STAC_API_URL") or None
    stac_asset_key: str = os.getenv("TITILER_EOPF_STAC_ASSET_KEY", "measurements")
    stac_timeout: float = float(os.getenv("TITILER_EOPF_STAC_TIMEOUT", "10"))
    stac_auth_token: str | None = os.getenv("TITILER_EOPF_STAC_AUTH_TOKEN") or None
    stac_headers_json: str | None = os.getenv("TITILER_EOPF_STAC_HEADERS_JSON") or None


settings = ResolverSettings()


def _normalized_base(url: str) -> str:
    return url.rstrip("/") + "/"


def _parse_extra_headers(raw: str | None) -> Dict[str, str]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
        if isinstance(value, dict):
            return {str(k): str(v) for k, v in value.items()}
    except Exception:
        pass
    return {}


def _http_get_json(url: str) -> Dict[str, Any]:
    headers = _parse_extra_headers(settings.stac_headers_json)
    if settings.stac_auth_token:
        headers["Authorization"] = f"Bearer {settings.stac_auth_token}"

    req = Request(url, headers=headers)
    with urlopen(req, timeout=settings.stac_timeout) as response:  # noqa: S310
        content = response.read().decode("utf-8")
    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object from {url}")
    return payload


def _item_self_href(item: Dict[str, Any]) -> str | None:
    links = item.get("links")
    if not isinstance(links, list):
        return None
    for link in links:
        if not isinstance(link, dict):
            continue
        if link.get("rel") == "self" and isinstance(link.get("href"), str):
            return link["href"]
    return None


def _resolve_item_asset_href_from_stac_api(collection_id: str, item_id: str) -> str:
    if not settings.stac_api_url:
        raise ValueError("TITILER_EOPF_STAC_API_URL is not set")

    stac_root = _normalized_base(settings.stac_api_url)
    item_url = urljoin(stac_root, f"collections/{collection_id}/items/{item_id}")
    item = _http_get_json(item_url)

    assets = item.get("assets")
    if not isinstance(assets, dict):
        raise ValueError(f"Item {collection_id}/{item_id} has no assets object")

    asset_obj = assets.get(settings.stac_asset_key)
    if not isinstance(asset_obj, dict):
        raise ValueError(
            f"Item {collection_id}/{item_id} missing asset '{settings.stac_asset_key}'"
        )

    href = asset_obj.get("href")
    if not isinstance(href, str) or not href:
        raise ValueError(
            f"Item {collection_id}/{item_id} asset '{settings.stac_asset_key}' has no href"
        )

    # Relative href: resolve against item self href when available; otherwise item URL.
    base = _item_self_href(item) or item_url
    return urljoin(base, href)


def _fallback_store_path(collection_id: str, item_id: str) -> str:
    return os.path.join(str(settings.store_url), collection_id, item_id) + ".zarr"


def DatasetPathParams(
    request: StarletteRequest,
    collection_id: Annotated[
        str,
        Path(description="Collection Identifier"),
    ],
    item_id: Annotated[str, Path(description="Item Identifier")],
) -> str:
    """Resolve dataset path for TiTiler reader.

    Resolution order:
    1) If TITILER_EOPF_STAC_API_URL is configured: fetch item from STAC API,
       resolve asset href from TITILER_EOPF_STAC_ASSET_KEY.
    2) Fallback to legacy store layout:
       {TITILER_EOPF_STORE_URL}/{collection_id}/{item_id}.zarr
    """
    if settings.stac_api_url:
        try:
            return _resolve_item_asset_href_from_stac_api(collection_id, item_id)
        except Exception:
            # Keep backward-compatible fallback behavior if STAC API lookup fails.
            return _fallback_store_path(collection_id, item_id)

    return _fallback_store_path(collection_id, item_id)


@dataclass
class XarrayParams(DefaultDependency):
    """Xarray Dataset options."""

    sel: Annotated[
        List[SelDimStr] | None,
        Query(description="Xarray indexing using `{dimension}={value}`."),
    ] = None

    method: Annotated[
        Literal["nearest", "pad", "ffill", "backfill", "bfill"] | None,
        Query(
            alias="sel_method",
            description="Xarray indexing method to use for inexact matches.",
        ),
    ] = None

    variables: Annotated[
        List[str] | None,
        Query(description="Variable names in form `{group}:{variable}`."),
    ] = None


@dataclass
class LayerParams(BidxParams, ExpressionParams, XarrayParams):
    """Variables/expression + indexes."""

    def __post_init__(self):
        if not self.variables and not self.expression:
            raise ValueError(
                "variables must be defined either via expression or variables options."
            )


@dataclass
class VariablesParams(DefaultDependency):
    """Variables endpoint options."""

    sel: Annotated[
        List[SelDimStr] | None,
        Query(description="Xarray indexing using `{dimension}={value}`."),
    ] = None

    method: Annotated[
        Literal["nearest", "pad", "ffill", "backfill", "bfill"] | None,
        Query(
            alias="sel_method",
            description="Xarray indexing method to use for inexact matches.",
        ),
    ] = None

    variables: Annotated[
        List[str] | None,
        Query(description="Variable names in form `{group}:{variable}`."),
    ] = None
