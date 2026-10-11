import numpy as np
from numpy.typing import NDArray
from skimage.filters import threshold_otsu


def apply_otsu_threshold(
    data: NDArray[np.float64] | NDArray[np.float32] | NDArray[np.uint16],
) -> NDArray[np.bool_]:
    """Return a boolean mask thresholded by Otsu method."""
    valid = data[np.isfinite(data)]
    result: NDArray[np.bool_] = data > threshold_otsu(valid)
    return result


def threshold(
    data: NDArray[np.float64] | NDArray[np.float32] | NDArray[np.uint16],
) -> NDArray[np.bool_]:
    """Backward-compatible alias for Otsu thresholding."""
    return apply_otsu_threshold(data)
