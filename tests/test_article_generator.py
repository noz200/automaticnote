from datetime import datetime, timezone

from auto_note_pipeline import ArticleGenerator, NewsItem


class _FakeOpenAI:
    def __init__(self, **kwargs):
        if "http_client" not in kwargs:
            raise TypeError("__init__() got an unexpected keyword argument 'proxies'")
        self.kwargs = kwargs


def test_create_client_falls_back_when_proxies_typeerror(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    client = ArticleGenerator._create_client(_FakeOpenAI)

    assert client.kwargs["api_key"] == "test-key"
    assert "http_client" in client.kwargs


def test_build_prompt_contains_future_and_agent_structure():
    item = NewsItem(
        title="AIエージェント活用の新潮流",
        url="https://example.com/news",
        published=datetime(2026, 3, 19, tzinfo=timezone.utc),
        source="Example News",
    )

    prompt = ArticleGenerator._build_prompt(item)

    assert "未来が変わる" in prompt
    assert "役割分担エージェント" in prompt
    assert "Market Analyst" in prompt
    assert "Opportunity Designer" in prompt
    assert item.title in prompt
