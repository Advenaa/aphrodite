"""Aphrodite product modules."""

from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import entry_points
from typing import Any

Handler = Callable[[str, list[str], dict[str, Any]], dict[str, Any]]
ADAPTER_ENTRY_POINT_GROUP = "aphrodite.adapters"


def discover_adapters() -> dict[str, Handler]:
    """Discover dispatch adapters published under the entry-point group.

    Entry-point name == system name; loaded value == dispatch handler.
    Third-party / overlay packages register adapters by declaring their own
    entry points in this group, so no public-tree imports are required.
    A failing entry point is skipped rather than breaking discovery.
    """
    adapters: dict[str, Handler] = {}
    for ep in entry_points(group=ADAPTER_ENTRY_POINT_GROUP):
        try:
            adapters[ep.name] = ep.load()
        except Exception:
            continue
    return adapters
