import asyncio
import json

import httpx
import pytest

from gov_erp.services.explanations import compose_explanation, prepare_facts
from gov_erp.settings import Settings

RESULT = {
    "departments": {"Saude": {"current": "42.00", "previous": "20.00"}},
    "source": "synthetic_erp",
}


def compose(payload=None, enabled=True, error=None):
    calls = []

    async def post(self, url, **kwargs):
        calls.append(kwargs["json"])
        if error:
            raise error
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    return post, calls, Settings(model_enabled=enabled)


def test_disabled_never_calls_model(monkeypatch):
    post, calls, config = compose(enabled=False)
    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    outcome = asyncio.run(compose_explanation("report", RESULT, "Resumo", config))
    assert outcome.status == "deterministic"
    assert calls == []


def test_legacy_timeout_loads_but_effective_budget_is_twenty(monkeypatch):
    config = Settings(_env_file=None, model_enabled=True, model_timeout_seconds=30)
    post, calls, _ = compose({"done": True, "message": {"content": '{"fact_ids":["f1"]}'}})
    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    budgets = []
    original_timeout = asyncio.timeout

    def timeout(seconds):
        budgets.append(seconds)
        return original_timeout(seconds)

    monkeypatch.setattr(asyncio, "timeout", timeout)
    outcome = asyncio.run(compose_explanation("report", RESULT, "Resumo", config))
    assert outcome.status == "model_validated"
    assert budgets == [20]
    assert len(calls) == 1


def test_valid_selection_is_backend_text(monkeypatch):
    post, calls, config = compose(
        {"done": True, "done_reason": "stop", "message": {"content": '{"fact_ids":["f1"]}'}}
    )
    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    outcome = asyncio.run(compose_explanation("report", RESULT, "Resumo", config))
    assert outcome.status == "model_validated"
    assert prepare_facts("report", RESULT)["f1"] in outcome.answer
    assert "sintéticos" in outcome.answer
    assert calls[0]["think"] is False
    assert calls[0]["format"]["additionalProperties"] is False
    assert "pergunta" not in json.dumps(calls[0])


@pytest.mark.parametrize(
    "content",
    [
        '{"fact_ids":[]}',
        '{"fact_ids":["unknown"]}',
        '{"fact_ids":["f1","f1"]}',
        '{"fact_ids":["f1"],"norma":"Lei inventada"}',
        "invalid",
        '{"fact_ids":[1]}',
        '{"fact_ids":["f1"],"canal":"whatsapp"}',
        '{"fact_ids":["f1"],"fact_ids":["f1"]}',
    ],
)
def test_invalid_selection_falls_back(monkeypatch, content):
    post, _, config = compose({"done": True, "message": {"content": content}})
    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    outcome = asyncio.run(compose_explanation("report", RESULT, "Resumo", config))
    assert outcome.status == "model_fallback"
    assert outcome.answer.startswith("Resumo")
    assert outcome.model is None


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"done": False, "message": {"content": '{"fact_ids":["f1"]}'}},
        {"done": True, "done_reason": "length", "message": {"content": '{"fact_ids":["f1"]}'}},
    ],
)
def test_incomplete_response_falls_back(monkeypatch, payload):
    post, _, config = compose(payload)
    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    assert (
        asyncio.run(compose_explanation("report", RESULT, "Resumo", config)).status
        == "model_fallback"
    )


def test_timeout_falls_back(monkeypatch):
    post, calls, config = compose(error=httpx.ReadTimeout("private content"))
    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    outcome = asyncio.run(compose_explanation("report", RESULT, "Resumo", config))
    assert outcome.reason == "timeout"
    assert len(calls) == 1


@pytest.mark.parametrize("intent,result", [("audit", RESULT), ("documents", {"sources": []})])
def test_ineligible_is_deterministic(monkeypatch, intent, result):
    post, calls, config = compose()
    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    assert (
        asyncio.run(compose_explanation(intent, result, "Resumo", config)).status == "deterministic"
    )
    assert calls == []
