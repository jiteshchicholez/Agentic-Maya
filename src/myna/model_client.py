from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openai import OpenAI


@dataclass(slots=True)
class CompletionResult:
    text: str
    tokens_used: int
    cost_usd: float
    model_used: str
    fallback_used: bool = False
    raw: Any | None = None


class OpenAICompatibleModelClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def _client(self, base_url: str) -> OpenAI:
        return OpenAI(base_url=base_url, api_key=self.api_key)

    def _invoke_completion(self, base_url: str, model: str, system_prompt: str, prompt: str) -> CompletionResult:
        client = self._client(base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        text = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        tokens = getattr(usage, "total_tokens", 0) or max(1, (len(system_prompt) + len(prompt) + len(text)) // 4)
        return CompletionResult(text=text, tokens_used=tokens, cost_usd=0.0, model_used=model, raw=response)

    def complete(
        self,
        *,
        model: str,
        fallback_model: str,
        base_url: str,
        system_prompt: str,
        prompt: str,
    ) -> CompletionResult:
        try:
            return self._invoke_completion(base_url, model, system_prompt, prompt)
        except Exception:
            if fallback_model == model:
                raise
            result = self._invoke_completion(base_url, fallback_model, system_prompt, prompt)
            result.fallback_used = True
            return result

    def embed(self, *, model: str, base_url: str, texts: list[str]) -> list[list[float]]:
        client = self._client(base_url)
        response = client.embeddings.create(model=model, input=texts)
        return [item.embedding for item in response.data]


class FakeModelClient:
    def __init__(
        self,
        completions: dict[str, str] | None = None,
        embeddings: dict[str, list[float]] | None = None,
        fail_primary_models: set[str] | None = None,
        **kwargs  # Accept additional kwargs for compatibility
    ):
        self.completions = completions or {}
        self.embeddings = embeddings or {}
        self.fail_primary_models = set(fail_primary_models or set())
        self.calls: list[dict[str, Any]] = []

    def complete(
        self,
        *,
        model: str,
        fallback_model: str,
        base_url: str,
        system_prompt: str,
        prompt: str,
    ) -> CompletionResult:
        self.calls.append({"type": "complete", "model": model, "fallback_model": fallback_model, "prompt": prompt})
        if model in self.fail_primary_models and fallback_model != model:
            text = self.completions.get(fallback_model, f"fallback:{fallback_model}:{prompt}")
            return CompletionResult(
                text=text,
                tokens_used=max(1, len(prompt) // 4),
                cost_usd=0.0,
                model_used=fallback_model,
                fallback_used=True,
            )
        text = self.completions.get(model, f"{model}:{prompt}")
        return CompletionResult(text=text, tokens_used=max(1, len(prompt) // 4), cost_usd=0.0, model_used=model)

    def embed(self, *, model: str, base_url: str, texts: list[str]) -> list[list[float]]:
        self.calls.append({"type": "embed", "model": model, "texts": texts})
        vectors: list[list[float]] = []
        for text in texts:
            if text in self.embeddings:
                vectors.append(self.embeddings[text])
            else:
                vectors.append([float(len(text)), float(sum(ord(char) for char in text) % 97)])
    def complete_with_fallback(self, messages: list[dict[str, str]]) -> CompletionResult:
        # For testing, simulate complete with fallback
        system_prompt = ""
        prompt = messages[-1]["content"] if messages else ""
        try:
            return self.complete(
                model="primary-model",
                fallback_model="fallback-model",
                base_url="http://test",
                system_prompt=system_prompt,
                prompt=prompt,
            )
        except Exception:
            # Fallback
            return self.complete(
                model="fallback-model",
                fallback_model="fallback-model",
                base_url="http://test",
                system_prompt=system_prompt,
                prompt=prompt,
            )


ModelClient = FakeModelClient
