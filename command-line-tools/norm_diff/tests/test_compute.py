import numpy as np

from norm_diff_tool.compute import normalized_difference


def test_normalized_difference_values():
    a = np.array([[2.0, 4.0]], dtype=np.float32)
    b = np.array([[1.0, 2.0]], dtype=np.float32)
    result = normalized_difference(a, b)
    np.testing.assert_allclose(result, np.array([[1 / 3, 1 / 3]], dtype=np.float32))

