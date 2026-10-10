"""Thin LLM client. Provider-agnostic via the OpenAI SDK + a base_url, so Groq today
and anything OpenAI-compatible tomorrow is a one-line env change. Returns None on any
failure so the caller can fall back to the offline grader - the demo never hard-fails."""
from __future__ import annotations
import json
from ..config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


def available() -> bool:
    return bool(LLM_API_KEY)


def _is_reasoning(model: str) -> bool:
    """gpt-oss models think before answering; that thinking counts against max_tokens."""
    return "gpt-oss" in (model or "").lower()


def _create(client, *, messages, max_tokens, temperature, json_mode):
    """One chat call. For reasoning models: keep thinking short and leave headroom for the
    answer. If the provider rejects the reasoning knob, retry once without it."""
    kwargs = dict(model=LLM_MODEL, messages=messages, temperature=temperature, max_tokens=max_tokens)
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    if _is_reasoning(LLM_MODEL):
        kwargs["max_tokens"] = max_tokens + 1500
        try:
            return client.chat.completions.create(**kwargs, extra_body={"reasoning_effort": "low"})
        except Exception:
            pass  # fall through: same request without the reasoning knob
    return client.chat.completions.create(**kwargs)


def chat_json(system: str, user: str, max_tokens: int = 1200) -> dict | None:
    """One chat call expecting a JSON object back. Returns parsed dict, or None on failure."""
    if not LLM_API_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, timeout=30)
        resp = _create(client,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=max_tokens, temperature=0.1, json_mode=True)
        return json.loads(resp.choices[0].message.content)
    except Exception as e:  # network, 429, bad JSON, SDK missing - all fall back
        print(f"[llm] falling back to offline grader: {e}")
        return None


def chat_text(system: str, user: str, max_tokens: int = 160) -> str | None:
    if not LLM_API_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, timeout=30)
        resp = _create(client,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=max_tokens, temperature=0.3, json_mode=False)
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"[llm] follow-up generation skipped: {e}")
        return None