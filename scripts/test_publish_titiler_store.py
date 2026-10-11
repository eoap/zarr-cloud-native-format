"""Publication must not disturb a working viewer when inputs are invalid."""

import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "publisher", Path(__file__).with_name("publish-titiler-store.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PublicationTests(unittest.TestCase):
    def test_invalid_input_preserves_current_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            good = root / "good"
            store = good / "collection" / "item.zarr"
            store.mkdir(parents=True)
            (store / "zarr.json").write_text("{}")
            destination = root / "published"
            module.publish(good, destination)
            bad = root / "bad"
            bad.mkdir()
            with self.assertRaises(ValueError):
                module.publish(bad, destination)
            self.assertEqual(destination.resolve(), good)
            second = root / "second"
            store = second / "collection" / "item.zarr"
            store.mkdir(parents=True)
            (store / "zarr.json").write_text("{}")
            module.publish(second, destination)
            self.assertEqual(destination.resolve(), second)

    def test_existing_directory_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "source" / "collection" / "item.zarr"
            store.mkdir(parents=True)
            (store / "zarr.json").write_text("{}")
            destination = root / "published"
            destination.mkdir()
            sentinel = destination / "keep"
            sentinel.write_text("existing output")
            with self.assertRaises(ValueError):
                module.publish(root / "source", destination)
            self.assertEqual(sentinel.read_text(), "existing output")


if __name__ == "__main__":
    unittest.main()
