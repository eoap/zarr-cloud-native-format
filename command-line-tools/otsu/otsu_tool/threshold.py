import numpy as np
from skimage.filters import threshold_otsu


def apply_otsu_threshold(data: np.ndarray) -> np.ndarray:
    """Return a boolean mask thresholded by Otsu method."""
    valid = data[np.isfinite(data)]
    return data > threshold_otsu(valid)


def threshold(data: np.ndarray) -> np.ndarray:
    """Backward-compatible alias for Otsu thresholding."""
    return apply_otsu_threshold(data)
