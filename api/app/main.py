from contextlib import asynccontextmanager

import redis
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from qdrant_client import QdrantClient
from sqlalchemy import text

from app.config import settings
from app.db import models  # noqa: F401 — регистрирует модели в Base.metadata
from app.db.session import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="SatışBot API", version="0.1.0", lifespan=lifespan)

redis_client = redis.Redis.from_url(settings.redis_url)
qdrant = QdrantClient(url=settings.qdrant_url)


def check_postgres() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def check_redis() -> bool:
    try:
        redis_client.ping()
        return True
    except Exception:
        return False


def check_qdrant() -> bool:
    try:
        qdrant.get_collections()
        return True
    except Exception:
        return False


@app.get("/health")
def health():
    checks = {
        "postgres": check_postgres(),
        "redis": check_redis(),
        "qdrant": check_qdrant(),
    }
    ok = all(checks.values())
    return JSONResponse(
        status_code=200 if ok else 503,
        content={"status": "ok" if ok else "degraded", "checks": checks},
    )