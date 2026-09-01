from __future__ import annotations

import json
import re
from typing import Any

from app.logging_config import get_logger

logger = get_logger("ai.json_utils")

JSON_REPAIR_SYSTEM = """You output ONLY valid JSON. You will receive a JSON document that
failed to parse together with the parse error. Fix the JSON (broken quotes, trailing
commas, unescaped newlines, truncated braces, comments, markdown fences) and respond
with the corrected JSON only - no prose, no code fences, no explanation.
Preserve every key and value from the original.
"""


def extract_json(text: str) -> str:
    """Extract the most likely JSON payload from a raw LLM response."""
    if not text:
        return ""
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.find("```", start)
        raw = text[start:end].strip() if end != -1 else text[start:].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.find("```", start)
        raw = text[start:end].strip() if end != -1 else text[start:].strip()
    else:
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            raw = text[brace_start:brace_end + 1]
        else:
            raw = text.strip()

    # Strip common model artifacts.
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    # Trailing commas: {..,] or [..,}
    raw = re.sub(r",\s*([\]}])", r"\1", raw)
    # Smart quotes emitted by some models.
    raw = raw.replace("\u201c", '"').replace("\u201d", '"')
    raw = raw.replace("\u2018", "'").replace("\u2019", "'")
    return raw


def try_parse_json(text: str) -> tuple[Any | None, str]:
    """Best-effort parse of model output as JSON. Returns (data, error)."""
    raw = extract_json(text)
    if not raw:
        return None, "empty response"
    try:
        return json.loads(raw), ""
    except json.JSONDecodeError as e:
        pass

    # Attempt progressively more aggressive cleanups.
    repaired = raw
    try:
        return json.loads(repaired), ""
    except json.JSONDecodeError as e1:
        pass

    # Remove // line comments.
    repaired = re.sub(r"^\s*//.*$", "", repaired, flags=re.MULTILINE)
    # Escape raw newlines inside string literals (very common LLM failure).
    repaired = re.sub(
        r'("(?:[^"\\]|\\.)*")',
        lambda m: m.group(1).replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t"),
        repaired,
        flags=re.DOTALL,
    )
    try:
        return json.loads(repaired), ""
    except json.JSONDecodeError as e2:
        return None, f"{e2.msg} (line {e2.lineno} col {e2.colno})"


async def repair_json_with_llm(ollama: Any, broken: str, error: str) -> str:
    """Ask the model to repair broken JSON. Returns fixed JSON text or ""."""
    prompt = (
        f"This JSON failed to parse.\n\nERROR: {error}\n\nBROKEN JSON:\n{broken[:6000]}\n\n"
        f"Return the corrected JSON only."
    )
    try:
        response = await ollama.generate(
            prompt=prompt,
            system=JSON_REPAIR_SYSTEM,
            temperature=0.0,
        )
    except Exception as e:
        logger.warning("JSON repair LLM call failed: %s", e)
        return ""
    if not response:
        return ""
    data, _ = try_parse_json(response)
    if data is not None:
        return extract_json(response)
    return ""
