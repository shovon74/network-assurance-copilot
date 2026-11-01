import json
import logging
import time
from typing import Annotated, Any, TypedDict
from fastapi import APIRouter, HTTPException, Request
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from .llm import call_llm
from .tools import get_alarms, get_kpi_trend, get_topology_neighbors, search_runbooks

logger = logging.getLogger("rca")
router = APIRouter(prefix="/incidents", tags=["rca"])


class RCAResultSchema(BaseModel):
    root_cause_code: str = Field(description="One of: transport_link_down, cell_congestion, site_power_failure, core_signaling_overload, interface_flapping, unknown")
    root_cause: str = Field(description="Clear explanation of the diagnosed root cause")
    root_cause_node: str | None = Field(description="The primary faulty node responsible for the incident")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    recommended_runbook: str | None = Field(description="Recommended runbook ID e.g. RB-TRN-001")
    evidence: list[str] = Field(default_factory=list, description="Specific cited evidence")


class RCAState(TypedDict):
    incident_id: int
    alarms: list[dict[str, Any]]
    nodes_involved: list[str]
    topology: dict[str, Any]
    kpis: list[dict[str, Any]]
    runbooks: list[dict[str, Any]]
    hypothesis: dict[str, Any] | None
    verification_passed: bool
    iterations: int
    tool_calls_log: list[str]
    final_output: dict[str, Any] | None


async def node_gather_evidence(state: RCAState, config: dict) -> dict[str, Any]:
    conn = config["configurable"]["conn"]
    incident_id = state["incident_id"]

    alarms = await get_alarms(conn, incident_id)
    nodes = list(dict.fromkeys(a["node_id"] for a in alarms))

    topo = {}
    for node in nodes:
        topo[node] = await get_topology_neighbors(conn, node)

    kpi_records = []
    for node in nodes:
        if node.startswith("CORE-MME"):
            samples = await get_kpi_trend(conn, node, "signaling_load_pct", window_minutes=25)
            kpi_records.append({"node": node, "metric": "signaling_load_pct", "samples": samples})
        else:
            tp_samples = await get_kpi_trend(conn, node, "dl_throughput_mbps", window_minutes=25)
            prb_samples = await get_kpi_trend(conn, node, "prb_utilization_pct", window_minutes=25)
            kpi_records.append({"node": node, "metric": "dl_throughput_mbps", "samples": tp_samples})
            kpi_records.append({"node": node, "metric": "prb_utilization_pct", "samples": prb_samples})

    logs = state.get("tool_calls_log", []) + [
        f"get_alarms(count={len(alarms)})",
        f"get_topology_neighbors({len(nodes)} nodes)",
        f"get_kpi_trend({len(kpi_records)} series)",
    ]

    return {
        "alarms": alarms,
        "nodes_involved": nodes,
        "topology": topo,
        "kpis": kpi_records,
        "tool_calls_log": logs,
    }


async def node_retrieve(state: RCAState, config: dict) -> dict[str, Any]:
    conn = config["configurable"]["conn"]
    alarm_summary = " ".join([f"{a['alarm_type']} on {a['node_id']}" for a in state["alarms"][:6]])
    query = f"Network incident with alarms: {alarm_summary}"
    hits = await search_runbooks(conn, query, k=4)

    logs = state.get("tool_calls_log", []) + [f"search_runbooks(query='{query[:40]}...', results={len(hits)})"]
    return {
        "runbooks": hits,
        "tool_calls_log": logs,
    }


async def node_hypothesize(state: RCAState, config: dict) -> dict[str, Any]:
    conn = config["configurable"]["conn"]

    alarms_str = "\n".join([f"- [{a['raised_at']}] {a['severity']} {a['alarm_type']} on {a['node_id']}: {a['message']}" for a in state["alarms"]])
    topo_str = json.dumps(state["topology"], indent=2)
    kpis_summary = []
    for k in state["kpis"]:
        recent_vals = [s["value"] for s in k["samples"][-5:]] if k["samples"] else []
        kpis_summary.append(f"- {k['node']} {k['metric']}: recent values={recent_vals}")
    kpi_str = "\n".join(kpis_summary)
    rb_str = "\n".join([f"- {r['doc_id']}: {r['title']} (score: {r['score']})\n  {r['content'][:250]}..." for r in state["runbooks"]])

    prompt = f"""
You are the Network Assurance Autonomous Operations Copilot. Diagnose this network incident.

AVAILABLE ALARMS:
{alarms_str}

TOPOLOGY CONTEXT:
{topo_str}

KPI TELEMETRY:
{kpi_str}

RELEVANT RUNBOOKS & PAST INCIDENTS (RAG):
{rb_str}

Respond with a JSON object strictly conforming to:
{{
  "root_cause_code": "transport_link_down" | "cell_congestion" | "site_power_failure" | "core_signaling_overload" | "interface_flapping" | "unknown",
  "root_cause": "detailed explanation of root cause",
  "root_cause_node": "primary failing node ID",
  "confidence": 0.0 to 1.0,
  "recommended_runbook": "e.g. RB-TRN-001",
  "evidence": ["list of supporting evidence facts"]
}}
"""

    llm_resp = await call_llm(
        conn,
        prompt=prompt,
        system_instruction="You are an expert telecom network assurance RCA agent. You must output valid JSON.",
        json_mode=True
    )

    hypothesis = llm_resp.get("parsed") or {
        "root_cause_code": "unknown",
        "root_cause": "Failed to parse structured RCA",
        "root_cause_node": None,
        "confidence": 0.0,
        "recommended_runbook": None,
        "evidence": []
    }

    logs = state.get("tool_calls_log", []) + ["llm_hypothesize"]
    return {
        "hypothesis": hypothesis,
        "tool_calls_log": logs,
        "iterations": state.get("iterations", 0) + 1,
    }


async def node_verify(state: RCAState, config: dict) -> dict[str, Any]:
    hypo = state.get("hypothesis", {})
    code = hypo.get("root_cause_code")
    node = hypo.get("root_cause_node")
    conf = hypo.get("confidence", 0.0)

    # Verification rule: check consistency
    passed = bool(code and code != "unknown" and node and conf >= 0.70)
    logs = state.get("tool_calls_log", []) + [f"verify_hypothesis(passed={passed})"]

    return {
        "verification_passed": passed,
        "tool_calls_log": logs,
    }


def should_reverify(state: RCAState) -> str:
    if state["verification_passed"] or state.get("iterations", 0) >= 2:
        return "conclude"
    return "hypothesize"


async def node_conclude(state: RCAState, config: dict) -> dict[str, Any]:
    final = state.get("hypothesis")
    return {"final_output": final}


def build_rca_graph():
    builder = StateGraph(RCAState)
    builder.add_node("gather_evidence", node_gather_evidence)
    builder.add_node("retrieve", node_retrieve)
    builder.add_node("hypothesize", node_hypothesize)
    builder.add_node("verify", node_verify)
    builder.add_node("conclude", node_conclude)

    builder.set_entry_point("gather_evidence")
    builder.add_edge("gather_evidence", "retrieve")
    builder.add_edge("retrieve", "hypothesize")
    builder.add_edge("hypothesize", "verify")
    builder.add_conditional_edges("verify", should_reverify, {
        "conclude": "conclude",
        "hypothesize": "hypothesize",
    })
    builder.add_edge("conclude", END)
    return builder.compile()


rca_agent_graph = build_rca_graph()


@router.post("/{incident_id}/rca")
async def run_rca_endpoint(incident_id: int, request: Request):
    t0 = time.perf_counter()
    pool = request.app.state.pool

    async with pool.connection() as conn:
        # Check incident exists
        cur = await conn.execute("SELECT id, status, domain, severity FROM incidents WHERE id = %s", (incident_id,))
        inc_row = await cur.fetchone()
        if not inc_row:
            raise HTTPException(status_code=404, detail="Incident not found")

        initial_state: RCAState = {
            "incident_id": incident_id,
            "alarms": [],
            "nodes_involved": [],
            "topology": {},
            "kpis": [],
            "runbooks": [],
            "hypothesis": None,
            "verification_passed": False,
            "iterations": 0,
            "tool_calls_log": [],
            "final_output": None,
        }

        final_state = await rca_agent_graph.ainvoke(
            initial_state,
            config={"configurable": {"conn": conn}}
        )

        output = final_state["final_output"] or {}
        latency_ms = int((time.perf_counter() - t0) * 1000)

        # Persist to rca_results
        cur = await conn.execute(
            """
            INSERT INTO rca_results
                (incident_id, root_cause, root_cause_node, confidence, evidence, recommended_runbook, model)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s)
            RETURNING id
            """,
            (
                incident_id,
                output.get("root_cause", "Unknown"),
                output.get("root_cause_node"),
                float(output.get("confidence", 0.0)),
                json.dumps(output.get("evidence", [])),
                output.get("recommended_runbook"),
                "gemini/langgraph_agent",
            )
        )
        rca_id = (await cur.fetchone())[0]

        # Persist audit record in agent_runs
        await conn.execute(
            """
            INSERT INTO agent_runs
                (incident_id, agent_name, model, status, tool_calls, final_output, latency_ms)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
            """,
            (
                incident_id,
                "rca_langgraph_agent",
                "gemini-2.0-flash",
                "success",
                json.dumps(final_state["tool_calls_log"]),
                json.dumps(output),
                latency_ms,
            )
        )

    return {
        "rca_id": rca_id,
        "incident_id": incident_id,
        "latency_ms": latency_ms,
        "result": output,
        "tool_calls": final_state["tool_calls_log"],
    }

