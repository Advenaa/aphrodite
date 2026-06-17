from __future__ import annotations

import importlib.metadata
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import aphrodite


def test_version_is_single_sourced():
    # pyproject.toml declares dynamic version = {attr = "aphrodite.__version__"},
    # so the installed distribution metadata must equal the in-package value.
    # If this fails after bumping aphrodite.__version__, reinstall the package
    # (e.g. `pip install -e ".[dev]"`) so the metadata is regenerated.
    assert importlib.metadata.version("aphrodite-sidecar") == aphrodite.__version__
