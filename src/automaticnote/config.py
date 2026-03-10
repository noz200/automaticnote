from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    note_api_base_url: str
    note_api_token: str


class ConfigError(ValueError):
    """Configuration is invalid."""


def load_settings() -> Settings:
    base_url = os.getenv("NOTE_API_BASE_URL", "https://note.com")
    token = os.getenv("NOTE_API_TOKEN", "")

    if not token:
        raise ConfigError("NOTE_API_TOKEN is required.")

    return Settings(note_api_base_url=base_url, note_api_token=token)
