"""The model endpoint an instance calls, per docs/content/deployments-and-approval.md 1.3.

Two settings name two endpoints: LIFEKIT_MODEL_SMALL for short completions (topic,
section, cover, digest line) and LIFEKIT_MODEL_ANSWER for answers. Each takes one of

    openai:<base_url>:<model>   an OpenAI-compatible server, such as the Nano NIM on a box
    hf:<model>                  Hugging Face inference through huggingface_hub

The answer setting falls back to the small one, and the small one falls back to the
Llama 3.1 8B stand-in on Hugging Face inference.

Reasoning models (Nemotron 3 Nano under Ollama, for one) think by default and spend the
whole token budget before writing an answer, so an OpenAI-style request asks for no
reasoning unless LIFEKIT_MODEL_THINKING=on.
"""

import os
from dataclasses import dataclass
from functools import lru_cache

DEFAULT = "hf:meta-llama/Llama-3.1-8B-Instruct"


@dataclass(frozen=True)
class Endpoint:
    scheme: str
    base_url: str | None
    model: str

    @property
    def name(self) -> str:
        return self.model


def parse(setting: str) -> Endpoint:
    scheme, _, rest = setting.partition(":")
    if scheme == "openai":
        # openai:http://host:port/v1:model  (the URL itself contains a colon)
        base_url, _, model = rest.rpartition(":")
        if not base_url or not model:
            raise ValueError(f"LIFEKIT_MODEL_*: expected openai:<base_url>:<model>, got {setting!r}")
        return Endpoint("openai", base_url.rstrip("/"), model)
    if scheme == "hf":
        return Endpoint("hf", None, rest)
    raise ValueError(f"LIFEKIT_MODEL_*: unknown scheme in {setting!r}")


@lru_cache(maxsize=2)
def endpoint(kind: str = "small") -> Endpoint:
    small = os.environ.get("LIFEKIT_MODEL_SMALL", DEFAULT)
    if kind == "answer":
        return parse(os.environ.get("LIFEKIT_MODEL_ANSWER", small))
    return parse(small)


def fetch_enabled() -> bool:
    return os.environ.get("LIFEKIT_FETCH", "on").lower() not in ("off", "0", "false", "no")


def ask(system: str, user: str, max_tokens: int = 300, kind: str = "small") -> str:
    """One chat completion: a system instruction and a user turn, low temperature."""
    return chat([{"role": "system", "content": system}, {"role": "user", "content": user}], max_tokens=max_tokens, kind=kind)


def chat(messages: list[dict], max_tokens: int = 300, kind: str = "small") -> str:
    """A chat completion over a full message list (system, then alternating turns)."""
    target = endpoint(kind)
    if target.scheme == "openai":
        import httpx

        body = {"model": target.model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.2}
        if os.environ.get("LIFEKIT_MODEL_THINKING", "off").lower() != "on":
            body["reasoning_effort"] = "none"
        response = httpx.post(f"{target.base_url}/chat/completions", json=body, timeout=300)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    from huggingface_hub import InferenceClient

    response = InferenceClient().chat_completion(
        model=target.model, messages=messages, max_tokens=max_tokens, temperature=0.2
    )
    return response.choices[0].message.content.strip()


def describe() -> dict:
    """For GET /api/config: what this instance calls, and whether the fetch pass runs."""
    return {
        "small": endpoint("small").name,
        "answer": endpoint("answer").name,
        "fetch": fetch_enabled(),
    }
