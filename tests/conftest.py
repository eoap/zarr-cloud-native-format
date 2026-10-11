"""Use the same helper-module search path as the repository's CLI scripts."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
