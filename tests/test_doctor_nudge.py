from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _stub_doctor_dependencies(monkeypatch):
    import aphrodite.doctor as doctor

    monkeypatch.setattr(doctor, "mcp_readiness", lambda root: {"ok": True})
    monkeypatch.setattr(doctor, "service_readiness", lambda root: {"ok": True})
    monkeypatch.setattr(doctor, "http_runtime_observability", lambda: {"ok": True})
    monkeypatch.setattr(doctor, "production_endpoint_preflight", lambda root: {"ok": True})
    return doctor


def test_doctor_ok_unaffected_when_nudge_offline(monkeypatch, tmp_path):
    import aphrodite.update as update

    doctor = _stub_doctor_dependencies(monkeypatch)
    monkeypatch.setattr(update, "_cache_path", lambda: tmp_path / "update-check.json")
    monkeypatch.setattr(update, "_latest_version", lambda: None)

    payload = doctor.doctor_payload(tmp_path)

    assert payload["ok"] is False
    assert "latest_version" in payload
    assert payload["latest_version"]["checked"] is False
    assert payload["latest_version"]["latest"] is None


def test_doctor_nudge_reports_available_without_changing_ok(monkeypatch, tmp_path):
    import aphrodite.update as update

    doctor = _stub_doctor_dependencies(monkeypatch)
    monkeypatch.setattr(update, "_cache_path", lambda: tmp_path / "update-check.json")
    monkeypatch.setattr(update, "_latest_version", lambda: "9.9.9")

    payload = doctor.doctor_payload(tmp_path)

    assert payload["ok"] is False
    assert payload["latest_version"]["checked"] is True
    assert payload["latest_version"]["latest"] == "9.9.9"
    assert payload["latest_version"]["update_available"] is True


def test_latest_version_nudge_reuses_fresh_cache(monkeypatch, tmp_path):
    import aphrodite.update as update

    calls = {"count": 0}

    def fake_latest():
        calls["count"] += 1
        return "9.9.9"

    monkeypatch.setattr(update, "_cache_path", lambda: tmp_path / "update-check.json")
    monkeypatch.setattr(update, "_latest_version", fake_latest)

    first = update.latest_version_nudge()
    second = update.latest_version_nudge()

    assert calls["count"] == 1
    assert first["latest"] == "9.9.9"
    assert second["latest"] == "9.9.9"
    assert second["update_available"] is True
