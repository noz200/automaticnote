import pytest

from automaticnote.config import ConfigError, load_settings


def test_load_settings_requires_token(monkeypatch):
    monkeypatch.delenv("NOTE_API_TOKEN", raising=False)

    with pytest.raises(ConfigError):
        load_settings()


def test_load_settings_accepts_defaults(monkeypatch):
    monkeypatch.setenv("NOTE_API_TOKEN", "dummy-token")
    monkeypatch.delenv("NOTE_API_BASE_URL", raising=False)

    settings = load_settings()

    assert settings.note_api_base_url == "https://note.com"
    assert settings.note_api_token == "dummy-token"
