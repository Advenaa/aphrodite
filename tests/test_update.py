from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_version_cli_prints_current_version(capsys):
    import aphrodite
    import aphrodite.cli as cli

    assert cli.main(["version"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["service"] == "aphrodite"
    assert payload["version"] == aphrodite.__version__


def test_update_check_reports_available_without_subprocess(monkeypatch, capsys):
    import aphrodite.cli as cli
    import aphrodite.update as update

    monkeypatch.setattr(update.importlib.metadata, "version", lambda package: "0.1.0")
    monkeypatch.setattr(update, "_latest_version", lambda: "9.9.9")

    def fail_run(*args, **kwargs):
        raise AssertionError("update --check must not run pip")

    monkeypatch.setattr(update.subprocess, "run", fail_run)

    assert cli.main(["update", "--check"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["action"] == "update"
    assert payload["before"] == "0.1.0"
    assert payload["latest"] == "9.9.9"
    assert payload["update_available"] is True
    assert payload["checked"] is True


def test_update_runs_pip_and_reads_metadata_after_cache_clear(monkeypatch, capsys):
    import aphrodite.cli as cli
    import aphrodite.update as update

    ran = {}
    state = {"cleared": False}

    def fake_version(package):
        assert package == update.PACKAGE
        return "0.2.0" if state["cleared"] else "0.1.0"

    class Proc:
        returncode = 0

    def fake_run(argv, **kwargs):
        ran["argv"] = argv
        ran["kwargs"] = kwargs
        return Proc()

    def fake_cache_clear():
        state["cleared"] = True

    monkeypatch.setattr(update.importlib.metadata, "version", fake_version)
    monkeypatch.setattr(update.importlib.metadata, "cache_clear", fake_cache_clear)
    monkeypatch.setattr(update.subprocess, "run", fake_run)
    monkeypatch.setattr(update, "_install_spec", lambda: update.INSTALL_SOURCE)

    assert cli.main(["update"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["before"] == "0.1.0"
    assert payload["after"] == "0.2.0"
    assert payload["updated"] is True
    assert state["cleared"] is True
    assert ran["argv"][:5] == [sys.executable, "-m", "pip", "install", "--upgrade"]
    assert ran["kwargs"]["text"] is True
    assert ran["kwargs"]["capture_output"] is True
    assert ran["kwargs"]["timeout"] == 300
    assert ran["kwargs"]["check"] is False


def test_install_spec_uses_pep_508_for_installed_extras(monkeypatch):
    import aphrodite.update as update

    def fake_find_spec(name):
        if name == "mcp":
            return object()
        return None

    monkeypatch.setattr(update.importlib.util, "find_spec", fake_find_spec)

    assert update._install_spec() == f"{update.PACKAGE}[mcp] @ {update.INSTALL_SOURCE}"


def test_update_check_is_offline_safe(monkeypatch):
    import aphrodite.update as update

    monkeypatch.setattr(update.importlib.metadata, "version", lambda package: "0.1.0")

    def fail_latest():
        raise OSError("offline")

    monkeypatch.setattr(update, "_latest_version", fail_latest)

    payload = update.update_payload(check=True)
    assert payload["ok"] is True
    assert payload["latest"] is None
    assert payload["checked"] is False
    assert payload["update_available"] is False
