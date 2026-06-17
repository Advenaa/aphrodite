"""Update helpers for the Aphrodite sidecar CLI."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__

INSTALL_SOURCE = "git+https://github.com/Advenaa/aphrodite"  # Flip to "aphrodite-sidecar" after PyPI publish.
GITHUB_RELEASES_URL = "https://api.github.com/repos/Advenaa/aphrodite/releases/latest"
PACKAGE = "aphrodite-sidecar"
_CACHE_TTL_SECONDS = 24 * 60 * 60
_UPDATE_COMMANDS = {"update", "version"}

if not hasattr(importlib.metadata, "cache_clear"):
    def _metadata_cache_clear() -> None:
        return None

    importlib.metadata.cache_clear = _metadata_cache_clear  # type: ignore[attr-defined]


def _install_spec() -> str:
    extras = []
    if importlib.util.find_spec("mcp") is not None:
        extras.append("mcp")
    if importlib.util.find_spec("acp") is not None:
        extras.append("acp")
    if extras:
        return f"{PACKAGE}[{','.join(extras)}] @ {INSTALL_SOURCE}"
    return INSTALL_SOURCE


def _latest_version() -> str | None:
    try:
        request = urllib.request.Request(
            GITHUB_RELEASES_URL,
            headers={"Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
        tag = str(payload.get("tag_name") or "").strip()
        if not tag:
            return None
        return tag.removeprefix("v")
    except Exception:
        return None


def _is_newer(latest: str | None, current: str) -> bool:
    if not latest:
        return False
    try:
        latest_parts = [int(part) for part in latest.split(".")]
        current_parts = [int(part) for part in current.split(".")]
        width = max(len(latest_parts), len(current_parts))
        latest_parts.extend([0] * (width - len(latest_parts)))
        current_parts.extend([0] * (width - len(current_parts)))
        return tuple(latest_parts) > tuple(current_parts)
    except Exception:
        return latest != current


def version_payload() -> dict[str, Any]:
    return {"service": "aphrodite", "version": __version__, "install_source": INSTALL_SOURCE}


def update_payload(check: bool = False) -> dict[str, Any]:
    before = importlib.metadata.version(PACKAGE)
    if check:
        try:
            latest = _latest_version()
        except Exception:
            latest = None
        return {
            "ok": True,
            "action": "update",
            "before": before,
            "latest": latest,
            "update_available": bool(latest and _is_newer(latest, before)),
            "checked": latest is not None,
        }

    install_source = _install_spec()
    proc = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", install_source],
        text=True,
        capture_output=True,
        timeout=300,
        check=False,
    )
    importlib.metadata.cache_clear()
    after = importlib.metadata.version(PACKAGE)
    return {
        "ok": proc.returncode == 0,
        "action": "update",
        "before": before,
        "after": after,
        "updated": before != after,
        "install_source": install_source,
        "summary": f"Aphrodite {before} -> {after}",
        "note": "Restart any running aphrodite service to use the new version.",
    }


def latest_version_nudge() -> dict[str, Any]:
    try:
        cache = _read_cache()
        if _cache_is_fresh(cache):
            return _nudge_payload(cache, reason=None)

        latest = _latest_version()
        if latest is None:
            return {
                "checked": False,
                "latest": None,
                "update_available": None,
                "install_source": INSTALL_SOURCE,
                "cached_at": None,
                "reason": "offline",
            }

        cache = {"latest": latest, "cached_at": _iso_now(), "cached_at_epoch": time.time()}
        _write_cache(cache)
        return _nudge_payload(cache, reason=None)
    except Exception:
        return {
            "checked": False,
            "latest": None,
            "update_available": None,
            "install_source": INSTALL_SOURCE,
            "cached_at": None,
            "reason": "offline",
        }


def maybe_notify_update(command: str | None = None) -> None:
    try:
        if os.environ.get("APHRODITE_NO_UPDATE_NOTIFIER"):
            return
        if os.environ.get("CI"):
            return
        if not sys.stderr.isatty():
            return
        if command in _UPDATE_COMMANDS:
            return

        cache = _read_cache()
        if not _cache_is_fresh(cache):
            latest = _latest_version()
            if latest is None:
                return
            cache = {"latest": latest, "cached_at": _iso_now(), "cached_at_epoch": time.time()}

        latest_value = cache.get("latest")
        latest = str(latest_value) if latest_value is not None else None
        if not _is_newer(latest, __version__):
            _write_cache(cache)
            return

        now = time.time()
        if cache.get("last_notified_version") == latest and now - float(cache.get("last_notified_at") or 0) < _CACHE_TTL_SECONDS:
            return

        print(
            f"Update available: Aphrodite {latest} (you have {__version__}).\n"
            "Run: aphrodite update\n"
            "Disable: APHRODITE_NO_UPDATE_NOTIFIER=1",
            file=sys.stderr,
        )
        cache["last_notified_version"] = latest
        cache["last_notified_at"] = now
        _write_cache(cache)
    except Exception:
        return


def _cache_path() -> Path:
    base_value = os.environ.get("XDG_CACHE_HOME")
    candidates = []
    if base_value:
        candidates.append(Path(base_value) / "aphrodite")
    try:
        candidates.append(Path.home() / ".cache" / "aphrodite")
    except Exception:
        pass
    candidates.append(Path(tempfile.gettempdir()) / "aphrodite")

    for directory in candidates:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            probe = directory / ".write-test"
            probe.write_text("", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return directory / "update-check.json"
        except Exception:
            continue
    return Path(tempfile.gettempdir()) / "aphrodite-update-check.json"


def _read_cache() -> dict[str, Any] | None:
    try:
        return json.loads(_cache_path().read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_cache(cache: dict[str, Any]) -> None:
    try:
        path = _cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache, sort_keys=True), encoding="utf-8")
    except Exception:
        return


def _cache_is_fresh(cache: dict[str, Any] | None) -> bool:
    if not cache:
        return False
    try:
        cached_at = float(cache.get("cached_at_epoch") or 0)
    except Exception:
        return False
    return time.time() - cached_at < _CACHE_TTL_SECONDS


def _nudge_payload(cache: dict[str, Any] | None, reason: str | None) -> dict[str, Any]:
    latest_value = cache.get("latest") if cache else None
    latest = str(latest_value) if latest_value is not None else None
    cached_at_value = cache.get("cached_at") if cache else None
    cached_at = str(cached_at_value) if cached_at_value is not None else None
    return {
        "checked": latest is not None,
        "latest": latest,
        "update_available": bool(latest and _is_newer(latest, __version__)),
        "install_source": INSTALL_SOURCE,
        "cached_at": cached_at,
        "reason": reason,
    }


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()
