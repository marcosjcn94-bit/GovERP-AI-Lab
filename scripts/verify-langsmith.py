from __future__ import annotations

import json
from pathlib import Path

from langsmith import Client

client = Client()
traces = list(
    client.list_runs(project_name="goverp-ai-lab-local", is_root=True, limit=20)
)
if not traces:
    raise RuntimeError("O projeto LangSmith nao possui traces raiz visiveis.")
if any(
    run.inputs not in ({}, None)
    or run.outputs not in ({}, None)
    or set((run.extra or {}).get("metadata", {})) - {"ls_run_depth"}
    for run in traces
):
    raise RuntimeError("LangSmith retornou campos que deveriam estar ocultos.")

Path(".runtime").mkdir(exist_ok=True)
Path(".runtime/langsmith-report.json").write_text(
    json.dumps(
        {
            "visible_root_traces": len(traces),
            "trace_visible": True,
            "inputs_hidden": True,
            "outputs_hidden": True,
            "metadata_hidden": True,
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print("Trace LangSmith recebido; entradas, saídas e metadados ocultos.")
