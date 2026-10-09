"""Local real-model gate; inputs are frozen and distinct from mock test fixtures."""

import asyncio
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from gov_erp.services.explanations import compose_explanation, prepare_facts, warnings
from gov_erp.settings import Settings

ROOT = Path(__file__).resolve().parents[1]


async def main():
    source = (ROOT / "tests/fixtures/qwen-heldout.json").read_bytes()
    dataset = json.loads(source)
    config = Settings(model_enabled=True, model_timeout_seconds=20)
    rows = []
    for case in dataset["cases"]:
        started = time.perf_counter()
        explanation = await compose_explanation(
            case["intent"], case["result"], "Resumo determinístico.", config
        )
        facts = prepare_facts(case["intent"], case["result"])
        suffix = warnings(case["intent"], case["result"])
        remainder = explanation.answer.removesuffix(suffix).strip()
        # Every visible model-composed sentence must be an approved backend sentence.
        for sentence in facts.values():
            remainder = remainder.replace(sentence, "")
        grounded = explanation.status != "model_validated" or not remainder.strip()
        assert grounded
        rows.append(
            {
                "id": case["id"],
                "status": explanation.status,
                "fallback_reason": explanation.reason,
                "seconds": round(time.perf_counter() - started, 3),
                "calls": 1,
                "retries": 0,
                "approved_facts_only": grounded,
                "answer": explanation.answer,
            }
        )
        print(case["id"], explanation.status, flush=True)
    report = {
        "measured_at_utc": datetime.now(UTC).isoformat(),
        "dataset_version": dataset["version"],
        "dataset_sha256": hashlib.sha256(source).hexdigest(),
        "model": config.model_name,
        "cases": rows,
        "accepted_compositions": sum(row["status"] == "model_validated" for row in rows),
        "fallbacks": sum(row["status"] == "model_fallback" for row in rows),
        "calls": 12,
        "retries": 0,
        "billing_cost": "not_measured_local_ollama",
        "human_review": "pending",
        "scope": "fact-selection contract; no production or semantic quality claim",
    }
    (ROOT / "artifacts/qwen-restricted-evaluation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    asyncio.run(main())
