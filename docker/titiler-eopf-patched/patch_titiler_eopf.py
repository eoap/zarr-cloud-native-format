from pathlib import Path


def patch_sel_regex() -> None:
    deps_path = Path("/usr/local/lib/python3.12/site-packages/titiler/xarray/dependencies.py")
    text = deps_path.read_text()
    old = r'pattern=r"^[^=]+=((nearest|pad|ffill|backfill|bfill)::)?[^=::]+$"'
    new = r'pattern=r"^[^=]+=((nearest|pad|ffill|backfill|bfill)::)?[^=]+$"'
    if old not in text:
        raise RuntimeError("Expected SelDimStr pattern was not found in titiler/xarray/dependencies.py")
    deps_path.write_text(text.replace(old, new))


def patch_eopf_reader_sel_parsing() -> None:
    reader_path = Path("/usr/local/lib/python3.12/site-packages/titiler/eopf/reader.py")
    text = reader_path.read_text()
    if "import numpy as np" not in text:
        text = text.replace("import xarray\n", "import xarray\nimport numpy as np\n")
    old = """        if sel:
            _idx: Dict[str, List] = {}
            for s in sel:
                val: Union[str, slice]
                dim, val = s.split("=")

                # cast string to dtype of the dimension
                if da[dim].dtype != "O":
                    val = da[dim].dtype.type(val)

                if dim in _idx:
                    _idx[dim].append(val)
                else:
                    _idx[dim] = [val]

            sel_idx = {k: v[0] if len(v) < 2 else v for k, v in _idx.items()}
            da = da.sel(sel_idx, method=method)
"""

    new = """        if sel:
            _idx: Dict[str, List] = {}
            effective_method = method
            allowed_methods = {"nearest", "pad", "ffill", "backfill", "bfill"}

            for s in sel:
                val: Union[str, slice]
                dim, val = s.split("=", 1)

                if "::" in val:
                    maybe_method, raw_val = val.split("::", 1)
                    if maybe_method in allowed_methods:
                        if effective_method is None:
                            effective_method = maybe_method
                        elif effective_method != maybe_method:
                            raise ValueError(
                                f"Conflicting selection methods provided: {effective_method} and {maybe_method}"
                            )
                        val = raw_val

                # cast string to dtype of the dimension
                if da[dim].dtype != "O":
                    if np.issubdtype(da[dim].dtype, np.datetime64):
                        if isinstance(val, str):
                            if val.isdigit():
                                val = np.datetime64(int(val), "ns")
                            else:
                                # xarray validator may pass ISO strings directly.
                                # Drop trailing Z and normalize to ns precision.
                                iso_val = val[:-1] if val.endswith("Z") else val
                                val = np.datetime64(iso_val, "ns")
                        else:
                            val = np.datetime64(val, "ns")
                    else:
                        val = da[dim].dtype.type(val)

                if dim in _idx:
                    _idx[dim].append(val)
                else:
                    _idx[dim] = [val]

            sel_idx = {k: v[0] if len(v) < 2 else v for k, v in _idx.items()}
            da = da.sel(sel_idx, method=effective_method)
"""
    if old not in text:
        raise RuntimeError("Expected sel parsing block was not found in titiler/eopf/reader.py")
    text = text.replace(old, new)
    reader_path.write_text(text)


def patch_eopf_reader_dataarray_variable_lookup() -> None:
    reader_path = Path("/usr/local/lib/python3.12/site-packages/titiler/eopf/reader.py")
    text = reader_path.read_text()
    old = 'if variable in tree[mt["asset"]].data_vars'
    new = (
        'if ('
        'hasattr(tree[mt["asset"]], "data_vars") and variable in tree[mt["asset"]].data_vars'
        ') or ('
        'hasattr(tree[mt["asset"]], "name") and tree[mt["asset"]].name == variable'
        ")"
    )
    if old not in text:
        raise RuntimeError(
            "Expected variable lookup condition was not found in titiler/eopf/reader.py"
        )
    reader_path.write_text(text.replace(old, new))


def patch_eopf_reader_dataarray_scale_access() -> None:
    reader_path = Path("/usr/local/lib/python3.12/site-packages/titiler/eopf/reader.py")
    text = reader_path.read_text()
    old = """                # Select the multiscale group and variable
                da = tree[scale][variable]
"""
    new = """                # Select the multiscale group and variable
                scale_node = tree[scale]
                if hasattr(scale_node, "data_vars"):
                    da = scale_node[variable]
                elif hasattr(scale_node, "name") and scale_node.name == variable:
                    da = scale_node
                else:
                    raise MissingVariables(
                        f"Variable '{variable}' not found in selected multiscale asset '{scale}'"
                    )
"""
    if old not in text:
        raise RuntimeError(
            "Expected multiscale variable selection block was not found in titiler/eopf/reader.py"
        )
    reader_path.write_text(text.replace(old, new))


def patch_get_multiscale_level_v1_variable_filter() -> None:
    reader_path = Path("/usr/local/lib/python3.12/site-packages/titiler/eopf/reader.py")
    text = reader_path.read_text()
    old = """    elif "layout" in dt.attrs.get("multiscales", {}):
        ms_resolutions = [
            (
                ms["asset"],
                min(abs(ms["spatial:transform"][0]), abs(ms["spatial:transform"][4])),
            )
            for ms in dt.attrs["multiscales"]["layout"]
        ]
"""
    new = """    elif "layout" in dt.attrs.get("multiscales", {}):
        ms_resolutions = [
            (
                ms["asset"],
                min(abs(ms["spatial:transform"][0]), abs(ms["spatial:transform"][4])),
            )
            for ms in dt.attrs["multiscales"]["layout"]
            if (
                hasattr(dt[ms["asset"]], "data_vars")
                and variable in dt[ms["asset"]].data_vars
            )
            or (
                hasattr(dt[ms["asset"]], "name")
                and dt[ms["asset"]].name == variable
            )
        ]
"""
    if old not in text:
        raise RuntimeError(
            "Expected GeoZarr V1 multiscale resolution block was not found in titiler/eopf/reader.py"
        )
    reader_path.write_text(text.replace(old, new))


if __name__ == "__main__":
    patch_sel_regex()
    patch_eopf_reader_sel_parsing()
    patch_eopf_reader_dataarray_variable_lookup()
    patch_eopf_reader_dataarray_scale_access()
    patch_get_multiscale_level_v1_variable_filter()
    print("Patched TiTiler-EOPF sel-time handling and item DataArray access.")
