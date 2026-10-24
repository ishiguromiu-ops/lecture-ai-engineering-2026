import sys
from types import SimpleNamespace

from app import ask as ask_module


class FakeModels:
    def __init__(self):
        self.kwargs = None
        self.calls = []
        self.response_text = "回答"
        self.failure = None

    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        self.calls.append(kwargs)
        if self.failure is not None:
            raise self.failure
        return SimpleNamespace(text=self.response_text, usage_metadata=None)


class FakeClient:
    def __init__(self, **kwargs):
        self.api_key = kwargs["api_key"]
        self.models = FakeModels()


def _fake_client(monkeypatch):
    client = FakeClient(api_key="test-key")
    monkeypatch.setattr(ask_module, "get_api_key", lambda: "test-key")
    monkeypatch.setattr(ask_module.genai, "Client", lambda **_: client)
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


def test_ask_sends_and_appends_history(monkeypatch):
    client = _fake_client(monkeypatch)
    history = []

    assert ask_module.ask("最初の質問", history) == "回答"
    assert ask_module.ask("次の質問", history) == "回答"

    first_contents = client.models.calls[0]["contents"]
    assert len(first_contents) == 1
    assert first_contents[0].role == "user"
    assert first_contents[0].parts[0].text == "最初の質問"

    second_contents = client.models.calls[1]["contents"]
    assert [message.role for message in second_contents] == ["user", "model", "user"]
    assert [message.parts[0].text for message in second_contents] == [
        "最初の質問",
        "回答",
        "次の質問",
    ]
    assert len(history) == 4


def test_ask_does_not_append_history_without_text_response(monkeypatch):
    client = _fake_client(monkeypatch)
    client.models.response_text = None
    history = []

    try:
        ask_module.ask("質問", history)
    except RuntimeError as error:
        assert "テキスト応答がありません" in str(error)
    else:
        raise AssertionError("テキスト応答がない場合は RuntimeError が必要")

    assert history == []


def test_ask_does_not_append_history_when_request_fails(monkeypatch):
    client = _fake_client(monkeypatch)
    client.models.failure = RuntimeError("request failed")
    history = []

    try:
        ask_module.ask("質問", history)
    except RuntimeError as error:
        assert str(error) == "request failed"
    else:
        raise AssertionError("リクエスト失敗時は例外が必要")

    assert history == []


def test_history_mode_defaults_to_off_and_reads_environment(monkeypatch):
    monkeypatch.delenv("AIE_HISTORY_MODE", raising=False)
    assert ask_module.get_initial_history_mode() is False

    monkeypatch.setenv("AIE_HISTORY_MODE", "ON")
    assert ask_module.get_initial_history_mode() is True

    monkeypatch.setenv("AIE_HISTORY_MODE", "off")
    assert ask_module.get_initial_history_mode() is False


def test_history_mode_rejects_invalid_environment_value(monkeypatch):
    monkeypatch.setenv("AIE_HISTORY_MODE", "sometimes")

    try:
        ask_module.get_initial_history_mode()
    except ValueError as error:
        assert "ON または OFF" in str(error)
    else:
        raise AssertionError("不正な値は ValueError が必要")


def test_repl_history_commands_and_questions(monkeypatch, capsys):
    client = _fake_client(monkeypatch)
    commands = iter(
        [
            "履歴OFFの質問",
            "/history on",
            "履歴ONの最初の質問",
            "履歴ONの次の質問",
            "/clear",
            "初期化後の質問",
            "/history off",
            "OFFの質問",
            "/history on",
            "再開後の質問",
            "/exit",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(commands))

    ask_module.run_repl(False)

    calls = client.models.calls
    assert calls[0]["contents"] == "履歴OFFの質問"
    assert len(calls[1]["contents"]) == 1
    assert [message.parts[0].text for message in calls[1]["contents"]] == [
        "履歴ONの最初の質問",
    ]
    assert len(calls[2]["contents"]) == 3
    assert [message.parts[0].text for message in calls[2]["contents"]] == [
        "履歴ONの最初の質問",
        "回答",
        "履歴ONの次の質問",
    ]
    assert len(calls[3]["contents"]) == 1
    assert calls[3]["contents"][0].parts[0].text == "初期化後の質問"
    assert calls[4]["contents"] == "OFFの質問"
    assert len(calls[5]["contents"]) == 1
    assert calls[5]["contents"][0].parts[0].text == "再開後の質問"

    output = capsys.readouterr().out
    assert "会話履歴を初期化しました。" in output
    assert "[history] OFF（会話履歴を消去しました）" in output


def test_main_without_question_starts_repl(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["app.ask"])
    monkeypatch.delenv("AIE_HISTORY_MODE", raising=False)
    modes = []
    monkeypatch.setattr(ask_module, "run_repl", modes.append)

    ask_module.main()

    assert modes == [False]


def test_main_with_question_keeps_one_shot_execution(monkeypatch, capsys):
    client = _fake_client(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["app.ask", "単発質問"])
    monkeypatch.delenv("AIE_HISTORY_MODE", raising=False)

    ask_module.main()

    assert client.models.calls[0]["contents"] == "単発質問"
    assert "回答" in capsys.readouterr().out
