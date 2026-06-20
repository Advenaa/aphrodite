"""Serve the Aphrodite FastAPI application."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn


def run_server(host: str, port: int, reload: bool = False) -> None:
    """Run Aphrodite with uvicorn."""

    uvicorn.run(
        "aphrodite.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
    )


def run_adapter_dev(adapter_path: str, host: str, port: int) -> None:
    """Run Aphrodite against a local adapter package with uvicorn reload."""
    adapter_dir = Path(adapter_path).expanduser().resolve()
    adapter_dir_str = str(adapter_dir)
    if adapter_dir_str not in sys.path:
        sys.path.insert(0, adapter_dir_str)

    adapter_module = f"+{adapter_dir.name}"
    configured_modules = os.environ.get("APHRODITE_MODULES", "").strip()
    os.environ["APHRODITE_MODULES"] = (
        f"{configured_modules},{adapter_module}" if configured_modules else adapter_module
    )

    uvicorn.run(
        "aphrodite.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=True,
        reload_dirs=[adapter_dir_str],
    )
