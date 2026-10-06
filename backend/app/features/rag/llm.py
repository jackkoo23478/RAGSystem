from typing import Protocol

import httpx

from app.core.config import settings


class LLMError(Exception):
    pass


class LLM(Protocol):
    def generate(self, messages: list[dict]) -> str: ...


class OllamaClient:
    def __init__(self, base_url=None, model=None, num_gpu=None, timeout=None, transport=None):
        self.base_url = base_url or settings.ollama_url
        self.model = model or settings.ollama_model
        self.num_gpu = settings.ollama_num_gpu if num_gpu is None else num_gpu
        self.timeout = timeout or settings.llm_timeout_seconds
        self.transport = transport

    def generate(self, messages: list[dict]) -> str:
        options = {"temperature": 0}
        if self.num_gpu is not None:
            options["num_gpu"] = self.num_gpu

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,          # 一次過攞完整答案,唔要逐字串流
            "options": options,
        }

        try:
            with httpx.Client(transport=self.transport, timeout=self.timeout) as client:
                response = client.post(f"{self.base_url}/api/chat", json=payload)
        except httpx.TimeoutException as e:
            raise LLMError("LLM request timed out") from e
        except httpx.HTTPError as e:
            raise LLMError("cannot reach the LLM server") from e

        if response.status_code != 200:
            raise LLMError(f"LLM server returned {response.status_code}: {response.text[:200]}")

        try:
            return response.json()["message"]["content"]
        except (KeyError, ValueError, TypeError) as e:
            raise LLMError("unexpected LLM response") from e


class FakeLLM:
    def __init__(self, answer="fake answer", error=None):
        self.answer = answer
        self.error = error
        self.calls = []                      

    def generate(self, messages: list[dict]) -> str:
        self.calls.append(messages)
        if self.error is not None:
            raise self.error
        return self.answer