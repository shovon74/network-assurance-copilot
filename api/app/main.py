import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from psycopg_pool import AsyncConnectionPool

from .config import settings
from .rag import router as rag_router
from .triage import router as triage_router
from .rca import router as rca_router
from .remediation import router as remediation_router

logger = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = AsyncConnectionPool(settings.db_conninfo, min_size=1, max_size=5, open=False)
    await pool.open(wait=True, timeout=30)
    app.state.pool = pool
    yield
    await pool.close()


app = FastAPI(title="Network Assurance Copilot", version="0.1.0", lifespan=lifespan)
app.include_router(triage_router)
app.include_router(rag_router)
app.include_router(rca_router)
app.include_router(remediation_router)


@app.get("/health")
async def health():
    try:
        async with app.state.pool.connection() as conn:
            cur = await conn.execute("SELECT 1")
            await cur.fetchone()
            cur = await conn.execute(
                "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
            )
            row = await cur.fetchone()
    except Exception:
        logger.exception("Health check failed")
        raise HTTPException(
            status_code=503, detail={"status": "unhealthy", "database": "down"}
        )
    return {"status": "ok", "database": "up", "pgvector": row[0] if row else None}
