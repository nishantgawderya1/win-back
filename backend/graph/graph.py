"""LangGraph StateGraph wiring. This is the bounded control flow.

detect -> diagnose -> plan -> {execute | halt | escalate}
execute -> {monitor | escalate}
monitor -> {plan | report}   (attempt ceiling also enforced here)
halt / escalate -> report -> END
"""
from __future__ import annotations

from datetime import datetime

from langgraph.graph import END, START, StateGraph

from backend.agents import diagnosis, detection, executor, monitor, planner, reporter
from backend.agents.nodes import escalate_node, halt_node
from backend.config import settings
from backend.graph.state import WinBackState


def route_from_planner(state: WinBackState) -> str:
    if state.halted:
        return "halt"
    if state.escalated:
        return "escalate"
    return "execute"


def route_from_executor(state: WinBackState) -> str:
    if state.escalated:
        return "escalate"
    return "monitor"


def route_from_monitor(state: WinBackState) -> str:
    if state.recovered or state.halted or state.escalated:
        return "report"
    if state.attempt_count >= settings.max_retry_attempts:
        return "report"
    # A retry/outreach has been scheduled for a future window (e.g. 9 AM, the
    # 1st of the month). We cannot act again within this run without violating
    # the cooldown, so defer to the report as "pending scheduled retry" rather
    # than looping straight back into a 0-minute cooldown halt.
    if state.retry_scheduled_at is not None and state.retry_scheduled_at > datetime.utcnow():
        return "report"
    return "plan"


def build_graph():
    graph = StateGraph(WinBackState)

    graph.add_node("detect", detection.detection_node)
    graph.add_node("diagnose", diagnosis.diagnosis_node)
    graph.add_node("plan", planner.planner_node)
    graph.add_node("execute", executor.executor_node)
    graph.add_node("monitor", monitor.monitor_node)
    graph.add_node("report", reporter.reporter_node)
    graph.add_node("halt", halt_node)
    graph.add_node("escalate", escalate_node)

    graph.add_edge(START, "detect")
    graph.add_edge("detect", "diagnose")
    graph.add_edge("diagnose", "plan")
    graph.add_conditional_edges(
        "plan", route_from_planner,
        {"execute": "execute", "halt": "halt", "escalate": "escalate"},
    )
    graph.add_conditional_edges(
        "execute", route_from_executor,
        {"monitor": "monitor", "escalate": "escalate"},
    )
    graph.add_conditional_edges(
        "monitor", route_from_monitor,
        {"plan": "plan", "report": "report"},
    )
    graph.add_edge("halt", "report")
    graph.add_edge("escalate", "report")
    graph.add_edge("report", END)

    return graph.compile()


app_graph = build_graph()
