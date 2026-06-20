from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from types import SimpleNamespace
from typing import Any

from fastapi import APIRouter
from fastapi.testclient import TestClient

import aphrodite.modules as modules
from aphrodite.app import create_app


class FakeEntryPoint:
    def __init__(self, name: str, loaded: object) -> None:
        self.name = name
        self._loaded = loaded

    def load(self) -> object:
        return self._loaded


def test_entry_point_adapter_is_discovered_mounted_and_dispatched(monkeypatch) -> None:
    router = APIRouter()

    @router.get("/ping")
    def ping() -> dict[str, bool]:
        return {"ok": True}

    def handle(
        action: str,
        payload: list[str],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "action": action,
            "payload": payload,
            "source": context["source"],
        }

    adapter = SimpleNamespace(
        handle=handle,
        router=router,
        requires_auth=False,
    )
    monkeypatch.delenv("APHRODITE_TRUSTED_ADAPTERS", raising=False)
    monkeypatch.setattr(
        modules,
        "entry_points",
        lambda group: [FakeEntryPoint("plugdemo", adapter)],
    )
    monkeypatch.setenv("APHRODITE_MODULES", "plugdemo")

    app = create_app()
    client = TestClient(app)

    specs, errors = modules.discover_adapter_specs()
    assert errors == {}
    assert specs["plugdemo"].requires_auth is False

    status = client.get("/status")
    assert status.status_code == 200
    assert "plugdemo" in status.json()["registered_systems"]

    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    assert "/plugdemo/ping" in openapi.json()["paths"]

    ping = client.get("/plugdemo/ping")
    assert ping.status_code == 200
    assert ping.json() == {"ok": True}

    dispatch = client.post("/dispatch/plugdemo:v1:greet:world")
    assert dispatch.status_code == 200
    assert dispatch.json() == {
        "ok": True,
        "system": "plugdemo",
        "version": "v1",
        "action": "greet",
        "payload": ["world"],
        "result": {
            "ok": True,
            "action": "greet",
            "payload": ["world"],
            "source": "http",
        },
    }
