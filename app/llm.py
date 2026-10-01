"""Optional LLM layer. With no ANTHROPIC_API_KEY the agents run fully rule-based."""
from __future__ import annotations

import json
import os
import re

MODEL = os.getenv("NYAYA_MODEL", "claude-sonnet-5-5")


def available() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def complete(system: str, user: str, max_tokens: int = 1500) -> str | None:
    if not available():
        return None
    try:
        import anthropic

        client = anthropic.Anthropic()
        r = client.messages.create(model=MODEL, max_tokens=max_tokens, system=system,
                                   messages=[{"role": "user", "content": user}])
        return "".join(b.text for b in r.content if getattr(b, "type", "") == "text").strip()
    except Exception:  # noqa: BLE001  (network, quota, bad key: fall back silently)
        return None


def complete_json(system: str, user: str) -> dict | None:
    out = complete(system + "\nReturn ONLY a JSON object. No prose, no code fences.", user)
    if not out:
        return None
    try:
        return json.loads(re.sub(r"^```(?:json)?|```$", "", out.strip(), flags=re.M).strip())
    except json.JSONDecodeError:
        return None


def localize(text: str, language_name: str) -> str | None:
    return complete(
        f"Translate into {language_name}. Keep numbers, names, section numbers and [placeholders] unchanged. "
        "Use simple, formal wording suitable for an official letter. Output only the translation.", text)
