from __future__ import annotations

import re
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class RequestState(TypedDict, total=False):
    question: str
    intent: Literal["report", "audit", "documents"]
    municipality_id: str
    user_id: str
    start_date: str | None
    end_date: str | None
    payload: dict[str, object]


def classify_question(question: str) -> str:
    normalized = question.casefold()
    if re.search(
        r"\b(auditoria|auditar|duplicad[oa]s?|revis[aã]o|revisar|suspeit[oa]s?)\b", normalized
    ):
        return "audit"
    if re.search(
        r"\b(despesa|despesas|pagamento|pagamentos|pago|pagas|liquidado|empenhad[oa]s?|receita|relat[oó]rio|compare|comparar)\b",
        normalized,
    ):
        return "report"
    return "documents"


def build_question_graph(checkpointer=None):
    graph = StateGraph(RequestState)

    def route(state: RequestState) -> dict[str, str]:
        return {"intent": classify_question(state["question"])}

    graph.add_node("route", route)
    graph.add_edge(START, "route")
    graph.add_edge("route", END)
    return graph.compile(checkpointer=checkpointer)


question_graph = build_question_graph()
