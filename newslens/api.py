"""NewsLens HTTP API.

Endpoints:
  GET  /healthz            — liveness + index stats
  POST /ingest             — crawl feeds and index new articles
  GET  /search?q=...       — hybrid retrieval, raw chunks
  GET  /ask?q=...          — RAG answer with citations
"""

import logging
import threading
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import config, crawler, indexer, rag

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("newslens")

app = FastAPI(title="NewsLens", version="0.1.0")

_UI = Path(__file__).resolve().parent.parent / "ui" / "index.html"
_ingest_lock = threading.Lock()
_ingest_state = {"running": False, "last": None}


class IngestRequest(BaseModel):
    per_feed: int = 10
    feeds: Optional[list] = None


@app.get("/")
def ui() -> FileResponse:
    return FileResponse(_UI)


@app.get("/healthz")
def healthz():
    try:
        stats = indexer.stats()
        return {"status": "ok", "index": stats, "ingest": _ingest_state}
    except Exception as exc:  # index may not exist yet
        return {"status": "degraded", "detail": str(exc), "ingest": _ingest_state}


def _run_ingest(per_feed: int, feeds: Optional[list]) -> None:
    cl = indexer.client()
    indexer.ensure_index(cl)
    new_articles, new_chunks, skipped = 0, 0, 0
    try:
        for article in crawler.crawl(feeds=feeds, per_feed=per_feed):
            if indexer.already_indexed(article.id, cl):
                skipped += 1
                continue
            n = indexer.index_article(article, cl)
            if n:
                new_articles += 1
                new_chunks += n
                logger.info("indexed %-60s %2d chunks", article.title[:60], n)
    finally:
        _ingest_state.update(
            running=False,
            last={"articles": new_articles, "chunks": new_chunks,
                  "skipped": skipped},
        )
        _ingest_lock.release()


@app.post("/ingest")
def ingest(req: IngestRequest):
    if not _ingest_lock.acquire(blocking=False):
        return {"started": False, "detail": "ingest already running"}
    _ingest_state["running"] = True
    threading.Thread(
        target=_run_ingest, args=(req.per_feed, req.feeds), daemon=True
    ).start()
    return {"started": True}


@app.get("/search")
def search(q: str = Query(..., min_length=2), k: int = 8):
    return {"query": q, "hits": indexer.hybrid_search(q, k=k)}


@app.get("/ask")
def ask(q: str = Query(..., min_length=2), k: int = 6):
    return rag.answer(q, k=k)
