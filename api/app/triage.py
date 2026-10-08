"""Rule-based triage (Step 2d): group raw alarms into incidents.

Rules:
  1. Group key = the alarm's parent node in the topology (or the node itself if it has no parent).
  2. Within a group, alarms closer together than GAP belong to the same incident.
  3. Incident severity/domain come from the most severe alarm in the cluster.
  4. Clusters whose worst alarm is only minor/warning are marked 'noise'.
"""
from collections import defaultdict
from datetime import timedelta

from fastapi import APIRouter, Request
from psycopg.rows import dict_row

router = APIRouter(prefix="/triage", tags=["triage"])

GAP = timedelta(seconds=300)
SEV_RANK = {"warning": 0, "minor": 1, "major": 2, "critical": 3}
OPEN_SEVERITIES = {"major", "critical"}


def split_clusters(rows):
    """rows must be sorted by raised_at and share one group key."""
    clusters, current = [], []
    for row in rows:
        if current and row["raised_at"] - current[-1]["raised_at"] > GAP:
            clusters.append(current)
            current = []
        current.append(row)
    if current:
        clusters.append(current)
    return clusters


@router.post("/run")
async def run_triage(request: Request):
    pool = request.app.state.pool
    summary = []

    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT a.id, a.raised_at, a.node_id, a.domain, a.alarm_type, a.severity,
                       COALESCE(t.parent_id, a.node_id) AS group_key
                FROM alarms a
                LEFT JOIN topology_nodes t ON t.node_id = a.node_id
                WHERE a.incident_id IS NULL
                ORDER BY a.raised_at
                """
            )
            rows = await cur.fetchall()

        by_group = defaultdict(list)
        for row in rows:
            by_group[row["group_key"]].append(row)

        clusters = []
        for group_rows in by_group.values():
            clusters.extend(split_clusters(group_rows))
        clusters.sort(key=lambda c: c[0]["raised_at"])

        for cluster in clusters:
            top = max(cluster, key=lambda r: SEV_RANK[r["severity"]])
            status = "open" if top["severity"] in OPEN_SEVERITIES else "noise"

            seen, duplicates = set(), 0
            for r in cluster:
                key = (r["node_id"], r["alarm_type"])
                if key in seen:
                    duplicates += 1
                else:
                    seen.add(key)

            cur2 = await conn.execute(
                "INSERT INTO incidents (domain, severity, status, opened_at) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (top["domain"], top["severity"], status, cluster[0]["raised_at"]),
            )
            incident_id = (await cur2.fetchone())[0]
            await conn.execute(
                "UPDATE alarms SET incident_id = %s WHERE id = ANY(%s)",
                (incident_id, [r["id"] for r in cluster]),
            )
            summary.append(
                {
                    "incident_id": incident_id,
                    "domain": top["domain"],
                    "severity": top["severity"],
                    "status": status,
                    "alarms": len(cluster),
                    "unique_alarms": len(seen),
                    "duplicates": duplicates,
                    "nodes": sorted({r["node_id"] for r in cluster}),
                }
            )

    return {
        "alarms_processed": len(rows),
        "incidents_created": len(summary),
        "incidents": summary,
    }
