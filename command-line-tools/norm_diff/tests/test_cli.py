from click.testing import CliRunner

from norm_diff_tool.cli import to_norm_diff


def test_cli_invokes_writer(monkeypatch):
    captured = {}

    def _fake_run_norm_diff(raster_a, raster_b):
        captured["raster_a"] = raster_a
        captured["raster_b"] = raster_b

    monkeypatch.setattr("norm_diff_tool.cli.run_norm_diff", _fake_run_norm_diff)

    runner = CliRunner()
    result = runner.invoke(to_norm_diff, ["a.tif", "b.tif"])
    assert result.exit_code == 0
    assert captured == {"raster_a": "a.tif", "raster_b": "b.tif"}

