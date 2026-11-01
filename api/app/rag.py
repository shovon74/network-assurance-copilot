import json
import pathlib
import re
from typing import Any

from fastapi import APIRouter, Query, Request
from fastembed import TextEmbedding

router = APIRouter(prefix="/rag", tags=["rag"])

MODEL_NAME = "BAAI/bge-small-en-v1.5"
RAG_ROOT = pathlib.Path("/app/rag")

_embedder: TextEmbedding | None = None


def get_embedder() -> TextEmbedding:
    global _embedder
    if _embedder is None:
        _embedder = TextEmbedding(model_name=MODEL_NAME)
    return _embedder


def embed_texts(texts: list[str]) -> list[str]:
    model = get_embedder()
    return [json.dumps(vec.tolist()) for vec in model.embed(texts)]


def parse_markdown_doc(path: pathlib.Path, doc_type: str) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    meta: dict[str, Any] = {}
    body = raw

    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) == 3:
            front_matter, body = parts[1], parts[2]
            for line in front_matter.strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    val = v.strip()
                    if val.lower() in ("true", "false"):
                        meta[k.strip()] = val.lower() == "true"
                    else:
                        meta[k.strip()] = val

    doc_id = str(meta.get("id", path.stem))
    title = str(meta.get("title", path.stem))
    domain = str(meta.get("domain", "UNKNOWN"))

    sections = re.split(r"(?m)^##\s+", body.strip())
    parsed_sections: list[str] = []
    for sec in sections[1:]:
        parsed_sections.append("## " + sec.strip())

    header = f"Document {doc_id} ({doc_type}) - {title} [Domain: {domain}]"
    chunks: list[str] = []
    if doc_type == "runbook" and len(parsed_sections) >= 3:
        part1 = "\n\n".join(parsed_sections[:2])
        part2 = "\n\n".join(parsed_sections[2:])
        chunks.append(f"{header}\n\n{part1}")
        chunks.append(f"{header}\n\n{part2}")
    else:
        chunks.append(f"{header}\n\n{body.strip()}")

    return {
        "doc_id": doc_id,
        "doc_type": doc_type,
        "title": title,
        "metadata": meta,
        "chunks": chunks,
    }


async def ingest_all(conn) -> dict[str, int]:
    docs: list[dict[str, Any]] = []
    runbooks_dir = RAG_ROOT / "runbooks"
    incidents_dir = RAG_ROOT / "past_incidents"

    if runbooks_dir.exists():
        for p in sorted(runbooks_dir.glob("*.md")):
            docs.append(parse_markdown_doc(p, "runbook"))
    if incidents_dir.exists():
        for p in sorted(incidents_dir.glob("*.md")):
            docs.append(parse_markdown_doc(p, "past_incident"))

    all_rows: list[tuple[str, str, str, int, str, str]] = []
    all_texts: list[str] = []
    for doc in docs:
        for idx, chunk_text in enumerate(doc["chunks"]):
            all_rows.append(
                (
                    doc["doc_id"],
                    doc["doc_type"],
                    doc["title"],
                    idx,
                    chunk_text,
                    json.dumps(doc["metadata"]),
                )
            )
            all_texts.append(chunk_text)

    vectors = embed_texts(all_texts) if all_texts else []

    async with conn.transaction():
        for (doc_id, doc_type, title, idx, content, meta_json), vec_str in zip(
            all_rows, vectors
        ):
            await conn.execute(
                """
                INSERT INTO runbook_chunks
                    (doc_id, doc_type, title, chunk_index, content, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s, %s::vector, %s::jsonb)
                ON CONFLICT (doc_id, chunk_index) DO UPDATE SET
                    doc_type = EXCLUDED.doc_type,
                    title = EXCLUDED.title,
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata
                """,
                (doc_id, doc_type, title, idx, content, vec_str, meta_json),
            )

    return {"documents": len(docs), "chunks": len(all_rows)}


async def _query_by_type(
    conn, vec_str: str, doc_type: str, limit: int
) -> list[dict[str, Any]]:
    cur = await conn.execute(
        """
        SELECT id, doc_id, doc_type, title, chunk_index, content, metadata, score
        FROM (
            SELECT DISTINCT ON (doc_id)
                id, doc_id, doc_type, title, chunk_index, content, metadata,
                ROUND((1 - (embedding <=> %s::vector))::numeric, 4) AS score,
                (embedding <=> %s::vector) AS dist
            FROM runbook_chunks
            WHERE doc_type = %s
            ORDER BY doc_id, embedding <=> %s::vector
        ) dedup
        ORDER BY dist ASC
        LIMIT %s
        """,
        (vec_str, vec_str, doc_type, vec_str, limit),
    )
    rows = await cur.fetchall()
    return [
        {
            "chunk_id": r[0],
            "doc_id": r[1],
            "doc_type": r[2],
            "title": r[3],
            "chunk_index": r[4],
            "content": r[5],
            "metadata": r[6],
            "score": float(r[7]),
        }
        for r in rows
    ]


async def retrieve(
    conn,
    query: str,
    k: int = 5,
    doc_type: str | None = None,
) -> list[dict[str, Any]]:
    vec_str = embed_texts([query])[0]
    if doc_type:
        return await _query_by_type(conn, vec_str, doc_type, k)

    # Stratified retrieval: ensure normative runbooks are never crowded out by past incidents
    rb_k = max(1, (k + 1) // 2)
    pi_k = max(1, k - rb_k)
    runbooks = await _query_by_type(conn, vec_str, "runbook", rb_k)
    incidents = await _query_by_type(conn, vec_str, "past_incident", pi_k)
    combined = sorted(runbooks + incidents, key=lambda x: x["score"], reverse=True)
    return combined[:k]


@router.post("/ingest")
async def ingest_endpoint(request: Request):
    async with request.app.state.pool.connection() as conn:
        result = await ingest_all(conn)
    return {"status": "ok", **result}


@router.get("/search")
async def search_endpoint(
    request: Request,
    q: str = Query(..., description="Natural language search query"),
    k: int = Query(5, ge=1, le=20),
    doc_type: str | None = Query(None),
):
    async with request.app.state.pool.connection() as conn:
        hits = await retrieve(conn, q, k=k, doc_type=doc_type)
    return {"query": q, "k": k, "results": hits}


SCENARIO_TEST_QUERIES = {
    "transport_link_down": (
        "RB-TRN-001",
        "TRANSPORT LINK_DOWN critical on TRN-AGG-01 and multiple S1_LINK_FAILURE and CELL_UNREACHABLE major alarms on SITE-001 SITE-002 SITE-003 with zero throughput",
    ),
    "cell_degradation": (
        "RB-RAN-001",
        "RAN HIGH_PRB_UTILIZATION minor and major followed by LOW_THROUGHPUT major on SITE-004 with PRB utilization ramping to 95%",
    ),
    "site_power_failure": (
        "RB-RAN-002",
        "RAN POWER_FAILURE critical followed by BATTERY_DISCHARGING CELL_DOWN and SITE_UNREACHABLE major alarms on single site SITE-002",
    ),
    "core_signaling_overload": (
        "RB-CORE-001",
        "CORE SIGNALING_OVERLOAD major CPU_HIGH major and repeated S1AP_REJECT_RATE_HIGH major alarms on CORE-MME-01",
    ),
    "flapping_interface": (
        "RB-TRN-002",
        "Repeated minor INTERFACE_FLAP alarms on transport switch TRN-AGG-02 with no LINK_DOWN and normal site throughput",
    ),
}


@router.post("/verify")
async def verify_scenarios(request: Request):
    report = []
    all_passed = True
    async with request.app.state.pool.connection() as conn:
        for scenario, (expected_rb, query) in SCENARIO_TEST_QUERIES.items():
            hits = await retrieve(conn, query, k=3)
            top3_ids = [h["doc_id"] for h in hits]
            passed = expected_rb in top3_ids
            if not passed:
                all_passed = False
            report.append(
                {
                    "scenario": scenario,
                    "expected_runbook": expected_rb,
                    "top3_doc_ids": top3_ids,
                    "top1_score": hits[0]["score"] if hits else None,
                    "passed": passed,
                }
            )
    return {"all_passed": all_passed, "scenarios": report}
