from types import SimpleNamespace

from app import ask as ask_module


class FakeModels:
    def __init__(self):
        self.kwargs = None

    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(text="回答", usage_metadata=None)


class FakeClient:
    def __init__(self, **kwargs):
        self.api_key = kwargs["api_key"]
        self.models = FakeModels()


def _fake_client(monkeypatch):
    client = FakeClient(api_key="test-key")
    monkeypatch.setattr(ask_module, "get_api_key", lambda: "test-key")
    monkeypatch.setattr(ask_module.genai, "Client", lambda **kwargs: client)
    return client


def test_ask_omits_temperature_when_unset(monkeypatch, capsys):
    client = _fake_client(monkeypatch)
    monkeypatch.setattr(ask_module, "TEMPERATURE", None)

    assert ask_module.ask("質問") == "回答"

    assert client.models.kwargs == {"model": ask_module.MODEL, "contents": "質問"}
    assert "[tokens]" in capsys.readouterr().out


def test_ask_passes_configured_temperature(monkeypatch):
    client = _fake_client(monkeypatch)
    monkeypatch.setattr(ask_module, "TEMPERATURE", 0.2)

    ask_module.ask("質問")

    assert client.models.kwargs["model"] == ask_module.MODEL
    assert client.models.kwargs["contents"] == "質問"
    assert client.models.kwargs["config"].temperature == 0.2
