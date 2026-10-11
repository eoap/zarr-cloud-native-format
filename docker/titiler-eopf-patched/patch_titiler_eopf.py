"""Guarded fixes for the pinned local-store TiTiler reader and GeoZarr v0.1."""

from pathlib import Path
import re
import sysconfig


SITE = Path(sysconfig.get_paths()["purelib"])


def replace_required(text: str, old: str, new: str, description: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(
            f"Expected exactly one {description} block in the pinned image"
        )
    return text.replace(old, new, 1)


def patch_sel_regex() -> None:
    path = SITE / "titiler/xarray/dependencies.py"
    text = path.read_text()
    old = r'pattern=r"^[^=]+=((nearest|pad|ffill|backfill|bfill)::)?[^=::]+$"'
    new = r'pattern=r"^[^=]+=((nearest|pad|ffill|backfill|bfill)::)?[^=]+$"'
    if old in text:
        path.write_text(text.replace(old, new))
    else:
        # The pinned xarray dependency already accepts ISO colons and inline methods.
        pattern = re.search(r'pattern=r"([^"\n]+)"', text)
        if not pattern or not all(
            re.fullmatch(pattern.group(1), value)
            for value in (
                "time=2021-06-08T18:49:21.024000000Z",
                "time=nearest::2021-06-08T18:49:21.024000000Z",
            )
        ):
            raise RuntimeError("Unsupported SelDimStr pattern in pinned image")


def patch_reader() -> None:
    path = SITE / "titiler/eopf/reader.py"
    text = path.read_text()
    if "import numpy as np" not in text:
        text = replace_required(
            text,
            "import xarray\n",
            "import xarray\nimport numpy as np\n",
            "xarray import",
        )
    text = replace_required(
        text,
        "values = [da[dimension].dtype.type(v) for v in values]",
        """if np.issubdtype(da[dimension].dtype, np.datetime64):
                    values = [
                        np.datetime64(int(v), "ns") if str(v).isdigit()
                        else np.datetime64(str(v).removesuffix("Z"), "ns")
                        for v in values
                    ]
                else:
                    values = [da[dimension].dtype.type(v) for v in values]""",
        "DSL selector dtype casting",
    )
    text = replace_required(
        text,
        'if variable in tree[mt["asset"]].data_vars',
        'if (hasattr(tree[mt["asset"]], "data_vars") and variable in tree[mt["asset"]].data_vars) or (hasattr(tree[mt["asset"]], "name") and tree[mt["asset"]].name == variable)',
        "multiscale variable lookup",
    )
    text = replace_required(
        text,
        "            da = tree[scale][variable]\n",
        """            scale_node = tree[scale]
            if hasattr(scale_node, "data_vars"):
                da = scale_node[variable]
            elif getattr(scale_node, "name", None) == variable:
                da = scale_node
            else:
                raise MissingVariables(f"Variable {variable} not found in {scale}")
""",
        "multiscale DataArray access",
    )
    text = replace_required(
        text,
        '        for ms in dt.attrs["multiscales"]["layout"]\n',
        '        for ms in dt.attrs["multiscales"]["layout"]\n'
        '        if (hasattr(dt[ms["asset"]], "data_vars") and variable in dt[ms["asset"]].data_vars)\n'
        '        or getattr(dt[ms["asset"]], "name", None) == variable\n',
        "multiscale resolution filtering",
    )
    compile(text, str(path), "exec")
    path.write_text(text)


if __name__ == "__main__":
    patch_sel_regex()
    patch_reader()
    print("Patched pinned TiTiler selector and GeoZarr DataArray handling")
