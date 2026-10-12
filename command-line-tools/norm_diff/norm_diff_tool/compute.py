import numpy as np
from numpy.typing import NDArray

np.seterr(divide="ignore", invalid="ignore")


def normalized_difference(
    array1: NDArray[np.float64] | NDArray[np.float32] | NDArray[np.uint16],
    array2: NDArray[np.float64] | NDArray[np.float32] | NDArray[np.uint16],
) -> NDArray[np.float64] | NDArray[np.float32] | NDArray[np.uint16]:
    """Compute normalized difference (a - b) / (a + b)."""
    result: NDArray[np.float64] | NDArray[np.float32] | NDArray[np.uint16] = (array1 - array2) / (
        array1 + array2
    )
    return result
