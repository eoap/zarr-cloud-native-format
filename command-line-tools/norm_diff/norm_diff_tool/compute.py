import numpy as np

np.seterr(divide="ignore", invalid="ignore")


def normalized_difference(array1: np.ndarray, array2: np.ndarray) -> np.ndarray:
    """Compute normalized difference (a - b) / (a + b)."""
    return (array1 - array2) / (array1 + array2)

