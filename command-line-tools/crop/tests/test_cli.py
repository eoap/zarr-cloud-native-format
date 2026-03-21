from click.testing import CliRunner

from crop_tool.cli import to_crop


def test_cli_invokes_run_crop(monkeypatch):
    captured = {}

    def _fake_run_crop(item_url, aoi, band, epsg, asset_signing):
        captured["item_url"] = item_url
        captured["aoi"] = aoi
        captured["band"] = band
        captured["epsg"] = epsg
        captured["asset_signing"] = asset_signing

    monkeypatch.setattr("crop_tool.cli.run_crop", _fake_run_crop)

    runner = CliRunner()
    result = runner.invoke(
        to_crop,
        [
            "--input-item",
            "item.json",
            "--aoi",
            "1,2,3,4",
            "--epsg",
            "EPSG:4326",
            "--band",
            "green",
            "--asset-signing",
            "mspc",
        ],
    )

    assert result.exit_code == 0
    assert captured == {
        "item_url": "item.json",
        "aoi": "1,2,3,4",
        "band": "green",
        "epsg": "EPSG:4326",
        "asset_signing": "mspc",
    }
