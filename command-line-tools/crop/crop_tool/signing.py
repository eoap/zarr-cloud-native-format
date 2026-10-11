from urllib.parse import urlparse

import pystac


def asset_href_needs_mspc_signing(href: str | None) -> bool:
    """Return True when an Azure Blob href should be signed for MSPC access.

    Mirrors stac-asset planetary computer logic:
    - host endswith `.blob.core.windows.net`
    - host is not `ai4edatasetspublicassets.blob.core.windows.net`
    - query does not already contain SAS token keys (`st`, `se`, `sp`)
    """
    if not href:
        return False

    parsed = urlparse(href)
    host = (parsed.hostname or "").lower()
    if not host.endswith(".blob.core.windows.net"):
        return False
    if host == "ai4edatasetspublicassets.blob.core.windows.net":
        return False

    query_keys = {pair.split("=", 1)[0] for pair in parsed.query.split("&") if pair}
    return not bool(query_keys & {"st", "se", "sp"})


def item_requires_mspc_signing(item: pystac.Item) -> bool:
    """Check whether item assets indicate MSPC signing is needed."""
    return any(asset_href_needs_mspc_signing(asset.href) for asset in item.get_assets().values())


def sign_item_for_mspc(item: pystac.Item) -> pystac.Item:
    """Sign item assets for Planetary Computer access using SAS tokens."""
    try:
        import planetary_computer
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Planetary Computer signing requested but dependency "
            "'planetary-computer' is not installed."
        ) from exc

    planetary_computer.sign_inplace(item)
    return item
