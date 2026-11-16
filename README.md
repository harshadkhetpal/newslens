# NewsLens — news intelligence with hybrid search + RAG

Crawl live news → clean & chunk → embed locally → index into **OpenSearch**
(BM25 + kNN vectors) → ask questions and get **cited answers**.

```
RSS feeds ──▶ crawler ──▶ chunker ──▶ embedder (sentence-transformers)
                                          │
                                          ▼
                    OpenSearch  ◀── hybrid index (BM25 + HNSW kNN)
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
      GET /search             GET /ask  ──▶ Claude (or extractive fallback)
            └───────────┬───────────┘
                        ▼
                   Web UI (/)
```

## Why this design

- **Hybrid retrieval** — BM25 catches exact names ("Nvidia", "COP31"),
  vectors catch paraphrase ("chip maker earnings"). One bool query blends both.
- **Local embeddings** — `all-MiniLM-L6-v2` runs on CPU, no per-token cost,
  no data leaves the machine during indexing.
- **Graceful degradation** — without an `ANTHROPIC_API_KEY`, `/ask` returns
  extractive cited passages instead of an error. The demo never breaks.
- **Idempotent ingestion** — article ids are content-addressed (sha1 of URL);
  re-crawls skip what's already indexed.
- **Polite crawling** — RSS discovery only, custom User-Agent, rate-limited.

## Quick start (Docker)

```bash
docker compose up -d           # OpenSearch + NewsLens API
open http://localhost:8800     # UI — click "Ingest latest news"
```

## Quick start (local)

```bash
pip install -r requirements.txt
# start OpenSearch (brew services start opensearch, or your own cluster)
uvicorn newslens.api:app --port 8800
python scripts/ingest.py       # or click "Ingest" in the UI
```

Optional: `export ANTHROPIC_API_KEY=...` for synthesised answers.

## API

| Endpoint | Description |
|---|---|
| `GET /healthz` | liveness + index stats (articles, chunks, per-source) |
| `POST /ingest` | crawl feeds, index new articles (async, deduped) |
| `GET /search?q=` | hybrid retrieval, raw scored chunks |
| `GET /ask?q=` | RAG answer with inline `[n]` citations |

## Configuration

Everything is env-driven (`newslens/config.py`): OpenSearch host/port,
index name, embedding model, chunk sizes, answer model. Feeds are curated
in config and extendable.

---
Built by [Harshad Khetpal](https://harshadkhetpal.github.io/) ·
🤖 Generated with [Claude Code](https://claude.com/claude-code)
