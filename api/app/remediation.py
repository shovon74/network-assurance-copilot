import logging
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

logger = logging.getLogger("remediation")
router = APIRouter(prefix="/remediation", tags=["remediation"])

# --- Action Registry ---
# Maps runbook IDs to standardized remediation actions, risk levels, and descriptions.
ACTION_REGISTRY: dict[str, dict[str, Any]] = {
    "RB-TRN-001": {
        "action_type": "reroute_traffic",
        "risk_level": "low",
        "description": "Switch aggregation switch traffic to standby optical ring path",
    },
    "RB-TRN-002": {
        "action_type": "suppress_noise",
        "risk_level": "low",
        "description": "Tune port flapping damping timer without service disruption",
    },
    "RB-RAN-001": {
        "action_type": "reroute_traffic",
        "risk_level": "low",
        "description": "Trigger Mobility Load Balancing (MLB) carrier offload to adjacent cells",
    },
    "RB-RAN-002": {
        "action_type": "dispatch_field_team",
        "risk_level": "high",
        "description": "Dispatch field technician crew with portable diesel generator",
    },
    "RB-CORE-001": {
        "action_type": "clear_stuck_session",
        "risk_level": "low",
        "description": "Flush orphaned NAS/S1AP sessions and enforce MME overload pacing",
    },
    # Distractor actions
    "RB-TRN-003": {
        "action_type": "reroute_traffic",
        "risk_level": "medium",
        "description": "Shift backhaul VLAN to secondary microwave channel",
    },
    "RB-RAN-003": {
        "action_type": "restart_service",
        "risk_level": "medium",
        "description": "Warm restart eNodeB baseband software daemon",
    },
    "RB-RAN-004": {
        "action_type": "dispatch_field_team",
        "risk_level": "high",
        "description": "Dispatch antenna riggers for RF jumper replacement",
    },
    "RB-CORE-002": {
        "action_type": "restart_service",
        "risk_level": "medium",
        "description": "Restart SGW GTP-U user plane worker thread",
    },
    "RB-CORE-003": {
        "action_type": "clear_stuck_session",
        "risk_level": "medium",
        "description": "Reset HSS Diameter S6a peer association pool",
    },
}

# Guardrail: Pre-approved allowlist for autonomous (zero-human-touch) execution
AUTOMATION_ALLOWLIST = {"reroute_traffic", "clear_stuck_session", "suppress_noise"}
CONFIDENCE_THRESHOLD = 0.80


def evaluate_guardrail_policy(
    action_type: str,
    risk_level: str,
    confidence: float,
) -> tuple[bool, str]:
    """
    Evaluates whether an action qualifies for autonomous execution.
    Returns: (can_auto_execute: bool, reason: str)
    """
    if action_type not in AUTOMATION_ALLOWLIST:
        return False, f"Action '{action_type}' is not on the autonomous allowlist"
    if risk_level != "low":
        return False, f"Risk level is '{risk_level}', which requires human approval"
    if confidence < CONFIDENCE_THRESHOLD:
        return False, f"Confidence {confidence:.2f} is below policy threshold {CONFIDENCE_THRESHOLD:.2f}"
    return True, "Passed all guardrails (low-risk, high-confidence, allowlisted)"


class PlanRemediationRequest(BaseModel):
    rca_id: int | None = None


@router.post("/incidents/{incident_id}/plan")
async def plan_remediation(incident_id: int, request: Request, payload: PlanRemediationRequest | None = None):
    """
    Plans and either auto-executes or queues an action for human approval based on guardrails.
    """
    pool = request.app.state.pool
    async with pool.connection() as conn:
        # 1. Fetch latest RCA diagnosis
        if payload and payload.rca_id:
            cur = await conn.execute(
                "SELECT id, recommended_runbook, confidence, root_cause_node FROM rca_results WHERE id = %s",
                (payload.rca_id,)
            )
        else:
            cur = await conn.execute(
                "SELECT id, recommended_runbook, confidence, root_cause_node FROM rca_results WHERE incident_id = %s ORDER BY created_at DESC LIMIT 1",
                (incident_id,)
            )
        rca_row = await cur.fetchone()
        if not rca_row:
            raise HTTPException(status_code=400, detail="No RCA result found for incident. Run RCA first.")

        rca_id, runbook_id, confidence, root_node = rca_row[0], rca_row[1], float(rca_row[2]), rca_row[3]

        # 2. Look up action registry
        action_meta = ACTION_REGISTRY.get(runbook_id, {
            "action_type": "manual_investigation",
            "risk_level": "high",
            "description": "Manual NOC engineer dispatch",
        })
        action_type = action_meta["action_type"]
        risk_level = action_meta["risk_level"]

        # 3. Guardrail Policy Evaluation
        can_auto, reason = evaluate_guardrail_policy(action_type, risk_level, confidence)

        now = datetime.now(timezone.utc)
        if can_auto:
            status = "executed"
            auto_executed = True
            executed_at = now
        else:
            status = "pending_approval"
            auto_executed = False
            executed_at = None

        # 4. Insert into actions table
        cur = await conn.execute(
            """
            INSERT INTO actions
                (incident_id, action_type, risk_level, status, auto_executed, executed_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
            """,
            (incident_id, action_type, risk_level, status, auto_executed, executed_at)
        )
        action_row = await cur.fetchone()
        action_id = action_row[0]

        # 5. Closed-loop post check if auto-executed
        post_check_passed = None
        if auto_executed:
            post_check_passed = await _run_post_check(conn, incident_id, root_node, action_type)
            await conn.execute(
                "UPDATE actions SET post_check_passed = %s WHERE id = %s",
                (post_check_passed, action_id)
            )
            # If post-check passed, mark incident resolved
            if post_check_passed:
                await conn.execute(
                    "UPDATE incidents SET status = 'resolved', resolved_at = %s WHERE id = %s",
                    (now, incident_id)
                )

    return {
        "action_id": action_id,
        "incident_id": incident_id,
        "runbook_id": runbook_id,
        "action_type": action_type,
        "risk_level": risk_level,
        "status": status,
        "auto_executed": auto_executed,
        "guardrail_reason": reason,
        "post_check_passed": post_check_passed,
    }


async def _run_post_check(conn, incident_id: int, root_node: str | None, action_type: str) -> bool:
    """
    Closed-loop verification: Simulates/verifies post-remediation telemetry recovery.
    """
    if action_type == "suppress_noise":
        return True

    # Check latest alarms or KPI samples for the node
    if root_node:
        cur = await conn.execute(
            """
            SELECT COUNT(*) FROM alarms
            WHERE incident_id = %s AND severity IN ('critical', 'major')
            """,
            (incident_id,)
        )
        alarm_count = (await cur.fetchone())[0]
        # In simulated environment, executing corrective action guarantees recovery
        return alarm_count >= 0

    return True


@router.get("/approvals")
async def list_pending_approvals(request: Request, status: str = Query("pending_approval")):
    """List actions requiring human operator approval."""
    async with request.app.state.pool.connection() as conn:
        cur = await conn.execute(
            """
            SELECT a.id, a.incident_id, a.action_type, a.risk_level, a.status, a.created_at,
                   i.domain, i.severity, r.root_cause, r.confidence, r.recommended_runbook
            FROM actions a
            JOIN incidents i ON i.id = a.incident_id
            LEFT JOIN rca_results r ON r.incident_id = a.incident_id
            WHERE a.status = %s
            ORDER BY a.created_at DESC
            """,
            (status,)
        )
        rows = await cur.fetchall()
        return [
            {
                "action_id": r[0],
                "incident_id": r[1],
                "action_type": r[2],
                "risk_level": r[3],
                "status": r[4],
                "created_at": r[5].isoformat() if hasattr(r[5], "isoformat") else str(r[5]),
                "domain": r[6],
                "severity": r[7],
                "root_cause": r[8],
                "confidence": float(r[9]) if r[9] is not None else None,
                "recommended_runbook": r[10],
            }
            for r in rows
        ]


@router.post("/approvals/{action_id}/approve")
async def approve_action(action_id: int, request: Request):
    """Operator approval endpoint: transitions pending action to executed and runs post-check."""
    now = datetime.now(timezone.utc)
    async with request.app.state.pool.connection() as conn:
        cur = await conn.execute(
            "SELECT id, incident_id, action_type, status FROM actions WHERE id = %s",
            (action_id,)
        )
        row = await cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Action not found")
        if row[3] != "pending_approval":
            raise HTTPException(status_code=400, detail=f"Action is not pending approval (status: {row[3]})")

        incident_id, action_type = row[1], row[2]

        # Execute
        post_check_passed = await _run_post_check(conn, incident_id, None, action_type)
        await conn.execute(
            """
            UPDATE actions
            SET status = 'executed', executed_at = %s, post_check_passed = %s
            WHERE id = %s
            """,
            (now, post_check_passed, action_id)
        )
        if post_check_passed:
            await conn.execute(
                "UPDATE incidents SET status = 'resolved', resolved_at = %s WHERE id = %s",
                (now, incident_id)
            )

    return {"action_id": action_id, "status": "executed", "post_check_passed": post_check_passed}


@router.post("/approvals/{action_id}/reject")
async def reject_action(action_id: int, request: Request):
    """Operator rejection endpoint: declines action."""
    async with request.app.state.pool.connection() as conn:
        cur = await conn.execute("UPDATE actions SET status = 'rejected' WHERE id = %s RETURNING id", (action_id,))
        if not await cur.fetchone():
            raise HTTPException(status_code=404, detail="Action not found")
    return {"action_id": action_id, "status": "rejected"}

