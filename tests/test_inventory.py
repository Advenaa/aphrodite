from __future__ import annotations

from aphrodite.inventory import modules_payload


def test_default_modules_are_active(monkeypatch):
    monkeypatch.setenv("APHRODITE_MODULES", "")

    payload = modules_payload()

    assert payload["ok"] is True
    assert payload["configured"] == ["image_gen", "skillopt", "acp_relay"]
    assert payload["active"] == ["image_gen", "skillopt", "acp_relay"]
    assert payload["missing"] == []
    assert payload["available"] == []
    for key in (
        "ok",
        "configured",
        "discovered",
        "active",
        "missing",
        "available",
        "hint",
    ):
        assert key in payload
    assert payload["hint"] == "All configured modules are installed and active."
    assert "pip install -e" not in payload["hint"]
    assert "Enable available modules" not in payload["hint"]


def test_missing_configured_module_marks_payload_unhealthy(monkeypatch):
    monkeypatch.setenv("APHRODITE_MODULES", "image_gen,mymod")

    payload = modules_payload()

    assert payload["ok"] is False
    assert payload["configured"] == ["image_gen", "mymod"]
    assert payload["active"] == ["image_gen"]
    assert payload["missing"] == ["mymod"]
    assert "pip install -e" in payload["hint"]
    assert "All configured modules are installed and active." not in payload["hint"]


def test_duplicate_configured_modules_are_deduped(monkeypatch):
    monkeypatch.setenv("APHRODITE_MODULES", "image_gen,image_gen")

    payload = modules_payload()

    assert payload["configured"] == ["image_gen"]
    assert payload["active"] == ["image_gen"]


def test_discovered_unconfigured_modules_are_available(monkeypatch):
    monkeypatch.setenv("APHRODITE_MODULES", "image_gen")

    payload = modules_payload()

    assert payload["available"] == ["acp_relay", "skillopt"]
    assert "Enable available modules by adding them to APHRODITE_MODULES." in payload["hint"]
    assert "pip install -e" not in payload["hint"]
