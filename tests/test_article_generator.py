from auto_note_pipeline import ArticleGenerator


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
