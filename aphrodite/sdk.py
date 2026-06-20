from __future__ import annotations

from typing import Any

from .modules import ADAPTER_ENTRY_POINT_GROUP, AdapterModule, AdapterSpec, Handler
from .paths import hermes_root, plugin_dir


def ok(**fields: Any) -> dict[str, Any]:
    return {"ok": True, **fields}


def err(error: str, *, error_type: str = "error", **fields: Any) -> dict[str, Any]:
    return {"ok": False, "error": error, "error_type": error_type, **fields}


__all__ = [
    "ADAPTER_ENTRY_POINT_GROUP",
    "AdapterModule",
    "AdapterSpec",
    "Handler",
    "err",
    "hermes_root",
    "ok",
    "plugin_dir",
]
