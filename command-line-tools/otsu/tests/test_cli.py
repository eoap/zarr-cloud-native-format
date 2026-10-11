from click.testing import CliRunner

from otsu_tool.cli import to_otsu


def test_cli_invokes_writer(monkeypatch):
    captured = {}

    def _fake_run_otsu(raster):
        captured["raster"] = raster

    monkeypatch.setattr("otsu_tool.cli.run_otsu", _fake_run_otsu)

    runner = CliRunner()
    result = runner.invoke(to_otsu, ["ndwi.tif"])

    assert result.exit_code == 0
    assert captured == {"raster": "ndwi.tif"}
