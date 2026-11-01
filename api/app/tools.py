from datetime import datetime, timezone, timedelta
from typing import Any
from .rag import retrieve

async def get_alarms(conn, incident_id: int) -> list[dict[str, Any]]:
    """Retrieve all alarms correlated to an incident."""
    cur = await conn.execute(
        """
        SELECT id, raised_at, node_id, domain, alarm_type, severity, message
        FROM alarms
        WHERE incident_id = %s
        ORDER BY raised_at ASC
        """,
        (incident_id,)
    )
    rows = await cur.fetchall()
    return [
        {
            "alarm_id": r[0],
            "raised_at": r[1].isoformat() if hasattr(r[1], "isoformat") else str(r[1]),
            "node_id": r[2],
            "domain": r[3],
            "alarm_type": r[4],
            "severity": r[5],
            "message": r[6],
        }
        for r in rows
    ]

async def get_kpi_trend(
    conn,
    node_id: str,
    metric: str,
    window_minutes: int = 30,
    reference_time: datetime | None = None
) -> list[dict[str, Any]]:
    """Retrieve KPI samples for a node and metric within a time window."""
    if reference_time is None:
        reference_time = datetime.now(timezone.utc)
    
    start_time = reference_time - timedelta(minutes=window_minutes)
    end_time = reference_time + timedelta(minutes=10)

    cur = await conn.execute(
        """
        SELECT sampled_at, value
        FROM kpi_samples
        WHERE node_id = %s
          AND metric = %s
          AND sampled_at BETWEEN %s AND %s
        ORDER BY sampled_at ASC
        """,
        (node_id, metric, start_time, end_time)
    )
    rows = await cur.fetchall()
    return [
        {
            "sampled_at": r[0].isoformat() if hasattr(r[0], "isoformat") else str(r[0]),
            "value": round(float(r[1]), 2)
        }
        for r in rows
    ]

async def get_topology_neighbors(conn, node_id: str) -> dict[str, Any]:
    """Retrieve parent and child topology neighbors for a given node."""
    cur = await conn.execute(
        """
        SELECT node_id, domain, node_type, parent_id
        FROM topology_nodes
        WHERE node_id = %s
        """,
        (node_id,)
    )
    current = await cur.fetchone()
    if not current:
        return {"node_id": node_id, "parent": None, "children": []}

    parent_id = current[3]

    cur = await conn.execute(
        """
        SELECT node_id, domain, node_type
        FROM topology_nodes
        WHERE parent_id = %s
        """,
        (node_id,)
    )
    child_rows = await cur.fetchall()

    return {
        "node_id": current[0],
        "domain": current[1],
        "node_type": current[2],
        "parent_id": parent_id,
        "children": [
            {"node_id": r[0], "domain": r[1], "node_type": r[2]}
            for r in child_rows
        ]
    }

async def search_runbooks(conn, query: str, k: int = 3) -> list[dict[str, Any]]:
    """Perform vector search over standard operating runbooks and past incidents."""
    return await retrieve(conn, query=query, k=k)

