from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_adapter_env_returns_named_lowercase_keys(monkeypatch):
    monkeypatch.setenv("APHRODITE_WEATHER_API_KEY", "secret")
    monkeypatch.setenv("APHRODITE_WEATHER_REGION", "us")
    monkeypatch.setenv("APHRODITE_PORT", "1234")

    from aphrodite.config import adapter_env

    assert adapter_env("weather") == {"api_key": "secret", "region": "us"}


def test_adapter_env_empty_when_no_match(monkeypatch):
    monkeypatch.delenv("APHRODITE_NOPE_X", raising=False)

    from aphrodite.config import adapter_env

    assert adapter_env("nope") == {}
