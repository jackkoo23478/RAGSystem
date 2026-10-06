import json

import httpx
import pytest

from app.features.rag.llm import FakeLLM, LLMError, OllamaClient

MESSAGES = [
    {"role": "system", "content": "rules"},
    {"role": "user", "content": "How many leave days?"},
]


def ok_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"message": {"role": "assistant", "content": "14 days [1]"}})


def make_client(handler, **kwargs):
    return OllamaClient(
        base_url="http://llm.test",
        model="test-model",
        transport=httpx.MockTransport(handler),
        **kwargs,
    )


def capture_request():
    """Return (handler, captured) where captured['request'] is filled when the client calls."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        captured["body"] = json.loads(request.content)
        return ok_handler(request)

    return handler, captured


# ---------- OllamaClient: success path ----------

def test_returns_the_message_content():
    assert make_client(ok_handler).generate(MESSAGES) == "14 days [1]"


def test_sends_the_chat_request_in_the_expected_shape():
    handler, captured = capture_request()

    make_client(handler).generate(MESSAGES)

    assert captured["request"].method == "POST"
    assert captured["request"].url == "http://llm.test/api/chat"
    body = captured["body"]
    assert body["model"] == "test-model"
    assert body["messages"] == MESSAGES
    assert body["stream"] is False  # one complete answer, not a stream of fragments
    assert body["options"]["temperature"] == 0  # deterministic answers


def test_num_gpu_is_sent_when_configured():
    handler, captured = capture_request()

    make_client(handler, num_gpu=0).generate(MESSAGES)

    assert captured["body"]["options"]["num_gpu"] == 0  # 0 is a real value (force CPU), not "unset"


def test_num_gpu_is_left_out_when_not_configured(monkeypatch):
    monkeypatch.setattr("app.features.rag.llm.settings.ollama_num_gpu", None)
    handler, captured = capture_request()

    make_client(handler).generate(MESSAGES)

    assert "num_gpu" not in captured["body"]["options"]


def test_defaults_come_from_settings(monkeypatch):
    monkeypatch.setattr("app.features.rag.llm.settings.ollama_url", "http://from-settings:1")
    monkeypatch.setattr("app.features.rag.llm.settings.ollama_model", "settings-model")
    monkeypatch.setattr("app.features.rag.llm.settings.llm_timeout_seconds", 7.5)

    client = OllamaClient()

    assert client.base_url == "http://from-settings:1"
    assert client.model == "settings-model"
    assert client.timeout == 7.5


# ---------- OllamaClient: failures all become LLMError ----------

@pytest.mark.parametrize("status", [404, 500, 503])
def test_error_status_becomes_llm_error_with_the_status_code(status):
    def handler(request):
        return httpx.Response(status, json={"error": "something went wrong"})

    with pytest.raises(LLMError, match=str(status)):
        make_client(handler).generate(MESSAGES)


def test_error_message_includes_the_server_detail():
    def handler(request):
        return httpx.Response(404, json={"error": "model 'x' not found"})

    with pytest.raises(LLMError, match="not found"):
        make_client(handler).generate(MESSAGES)


def test_response_without_message_becomes_llm_error():
    def handler(request):
        return httpx.Response(200, json={"unexpected": 1})

    with pytest.raises(LLMError, match="unexpected"):
        make_client(handler).generate(MESSAGES)


def test_response_that_is_not_json_becomes_llm_error():
    def handler(request):
        return httpx.Response(200, text="this is not json")

    with pytest.raises(LLMError):
        make_client(handler).generate(MESSAGES)


def test_timeout_becomes_llm_error():
    def handler(request):
        raise httpx.ReadTimeout("too slow", request=request)

    with pytest.raises(LLMError, match="timed out"):
        make_client(handler).generate(MESSAGES)


def test_unreachable_server_becomes_llm_error():
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(LLMError, match="cannot reach"):
        make_client(handler).generate(MESSAGES)


def test_original_error_is_kept_as_the_cause():
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(LLMError) as info:
        make_client(handler).generate(MESSAGES)

    assert isinstance(info.value.__cause__, httpx.ConnectError)


# ---------- FakeLLM ----------

def test_fake_llm_returns_the_configured_answer():
    assert FakeLLM(answer="canned").generate(MESSAGES) == "canned"


def test_fake_llm_records_the_messages_it_received():
    llm = FakeLLM()

    llm.generate(MESSAGES)
    llm.generate([{"role": "user", "content": "second"}])

    assert llm.calls[0] == MESSAGES
    assert len(llm.calls) == 2


def test_fake_llm_can_simulate_a_failure():
    llm = FakeLLM(error=LLMError("boom"))

    with pytest.raises(LLMError, match="boom"):
        llm.generate(MESSAGES)
    assert len(llm.calls) == 1  # the call is recorded even when it fails


# ---------- real Ollama (slow) ----------

@pytest.mark.slow
def test_real_ollama_answers():
    try:
        answer = OllamaClient().generate([{"role": "user", "content": "Reply with the single word: pong"}])
    except LLMError as e:
        pytest.skip(f"Ollama is not usable here: {e}")

    assert answer.strip() != ""
