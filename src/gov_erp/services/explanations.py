"""The model selects approved fact IDs; only the backend authors visible text."""

import asyncio
import json
from dataclasses import dataclass

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from gov_erp.settings import Settings


class FactSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    fact_ids: list[str] = Field(min_length=1, max_length=5)


@dataclass(frozen=True)
class Explanation:
    answer: str
    status: str
    model: str | None = None
    reason: str | None = None


def prepare_facts(intent: str, result: dict) -> dict[str, str]:
    sentences = []
    if intent == "report":
        for name, values in sorted(result.get("departments", {}).items()):
            sentences.append(
                f"{name}: despesas pagas de R$ {values['current']} no período atual "
                f"e R$ {values['previous']} no período anterior."
            )
    elif intent == "documents":
        for source in result.get("sources", []):
            sentences.append(
                f"Fonte disponível para revisão: {source['title']}. Origem: {source['source_url']}."
            )
    return {f"f{index}": sentence for index, sentence in enumerate(sentences, 1)}


def warnings(intent: str, result: dict) -> str:
    notices = []
    if result.get("source") == "synthetic_erp" or any(
        source.get("source_kind") == "synthetic" for source in result.get("sources", [])
    ):
        notices.append("Dados sintéticos de demonstração.")
    if intent == "documents" and any(
        not source.get("vigency_verified") for source in result.get("sources", [])
    ):
        notices.append("Vigência não verificada; confira a fonte antes de agir.")
    return " ".join(notices)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_key")
        result[key] = value
    return result


async def compose_explanation(
    intent: str, result: dict, summary: str, config: Settings
) -> Explanation:
    suffix = warnings(intent, result)
    deterministic = " ".join(part for part in (summary, suffix) if part)
    facts = prepare_facts(intent, result)
    if not config.model_enabled or not facts:
        return Explanation(deterministic, "deterministic")
    schema = FactSelection.model_json_schema()
    schema["properties"]["fact_ids"]["items"]["enum"] = list(facts)
    schema["properties"]["fact_ids"]["uniqueItems"] = True
    body = {
        "model": config.model_name,
        "stream": False,
        "think": False,
        "format": schema,
        "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 128},
        "messages": [
            {
                "role": "system",
                "content": "Selecione e ordene de um a cinco IDs únicos dos fatos. Retorne somente o JSON fact_ids.",
            },
            {"role": "user", "content": json.dumps(facts, ensure_ascii=True)},
        ],
    }
    reason = "invalid_output"
    timeout_seconds = min(config.model_timeout_seconds, 20)
    try:
        async with asyncio.timeout(timeout_seconds):
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(config.model_url.rstrip("/") + "/api/chat", json=body)
                response.raise_for_status()
                payload = response.json()
        if not isinstance(payload, dict) or payload.get("done") is not True:
            return Explanation(deterministic, "model_fallback", reason="incomplete_response")
        if payload.get("done_reason") not in (None, "stop"):
            return Explanation(deterministic, "model_fallback", reason="truncated_response")
        message = payload.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or len(content) > 2048:
            raise ValueError("invalid_content")
        selection = FactSelection.model_validate(
            json.loads(content, object_pairs_hook=_unique_object)
        )
        ids = selection.fact_ids
        if len(set(ids)) != len(ids) or any(key not in facts for key in ids):
            raise ValueError("invalid_ids")
        answer = " ".join([*(facts[key] for key in ids), suffix]).strip()
        return Explanation(answer, "model_validated", config.model_name)
    except (TimeoutError, httpx.TimeoutException):
        reason = "timeout"
    except httpx.HTTPError:
        reason = "unavailable"
    except (ValueError, ValidationError):
        pass
    return Explanation(deterministic, "model_fallback", reason=reason)
