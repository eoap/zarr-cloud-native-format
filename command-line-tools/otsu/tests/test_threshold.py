import numpy as np

from otsu_tool.threshold import apply_otsu_threshold, threshold


def test_threshold_returns_boolean_mask():
    data = np.array([[0.0, 0.0, 10.0, 10.0]], dtype=np.float32)
    mask = apply_otsu_threshold(data)

    assert mask.dtype == np.bool_
    assert mask.shape == data.shape


def test_threshold_alias_matches_main_function():
    data = np.array([[0.0, 1.0, 100.0]], dtype=np.float32)
    np.testing.assert_array_equal(threshold(data), apply_otsu_threshold(data))
