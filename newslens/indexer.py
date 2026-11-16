"""OpenSearch index management and hybrid (BM25 + kNN) retrieval."""

import logging
from typing import Any, Dict, List, Optional

from opensearchpy import OpenSearch, helpers

from . import config, chunker, embedder
from .crawler import Article

logger = logging.getLogger(__name__)

MAPPING = {
    "settings": {
        "index": {"knn": True},
    },
    "mappings": {
        "properties": {
            "article_id": {"type": "keyword"},
            "url": {"type": "keyword"},
            "title": {"type": "text"},
            "source": {"type": "keyword"},
            "published": {"type": "date", "ignore_malformed": True},
            "chunk_index": {"type": "integer"},
            "text": {"type": "text"},
            "embedding": {
                "type": "knn_vector",
                "dimension": config.EMBEDDING_DIM,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "lucene",
                },
            },
        }
    },
}


def client() -> OpenSearch:
    return OpenSearch(
        hosts=[{"host": config.OPENSEARCH_HOST, "port": config.OPENSEARCH_PORT}],
        use_ssl=False,
        verify_certs=False,
        timeout=30,
    )


def ensure_index(cl: Optional[OpenSearch] = None) -> None:
    cl = cl or client()
    if not cl.indices.exists(index=config.INDEX_NAME):
        cl.indices.create(index=config.INDEX_NAME, body=MAPPING)
        logger.info("created index %s", config.INDEX_NAME)


def index_article(article: Article, cl: Optional[OpenSearch] = None) -> int:
    """Chunk, embed, and upsert one article. Returns number of chunks."""
    cl = cl or client()
    chunks = chunker.chunk_text(f"{article.title}\n{article.text}")
    if not chunks:
        return 0
    vectors = embedder.embed(chunks)
    actions = [
        {
            "_op_type": "index",
            "_index": config.INDEX_NAME,
            "_id": f"{article.id}:{i}",
            "article_id": article.id,
            "url": article.url,
            "title": article.title,
            "source": article.source,
            "published": article.published or None,
            "chunk_index": i,
            "text": text,
            "embedding": vec,
        }
        for i, (text, vec) in enumerate(zip(chunks, vectors))
    ]
    helpers.bulk(cl, actions)
    return len(actions)


def already_indexed(article_id: str, cl: Optional[OpenSearch] = None) -> bool:
    cl = cl or client()
    return bool(cl.exists(index=config.INDEX_NAME, id=f"{article_id}:0"))


def hybrid_search(query: str, k: int = 8,
                  cl: Optional[OpenSearch] = None) -> List[Dict[str, Any]]:
    """BM25 and kNN in one bool query; Lucene kNN scores blend with text scores.

    Reciprocal-rank-fusion would be the production choice; a bool-should blend
    keeps the demo dependency-free on older cluster versions.
    """
    cl = cl or client()
    vector = embedder.embed_one(query)
    body = {
        "size": k,
        "query": {
            "bool": {
                "should": [
                    {"multi_match": {"query": query,
                                     "fields": ["title^2", "text"]}},
                    {"knn": {"embedding": {"vector": vector, "k": k}}},
                ]
            }
        },
        "_source": {"excludes": ["embedding"]},
        "collapse": {"field": "article_id"},
    }
    res = cl.search(index=config.INDEX_NAME, body=body)
    hits = []
    for h in res["hits"]["hits"]:
        doc = h["_source"]
        doc["score"] = h["_score"]
        hits.append(doc)
    return hits


def stats(cl: Optional[OpenSearch] = None) -> Dict[str, Any]:
    cl = cl or client()
    count = cl.count(index=config.INDEX_NAME)["count"]
    agg = cl.search(index=config.INDEX_NAME, body={
        "size": 0,
        "aggs": {
            "sources": {"terms": {"field": "source", "size": 20}},
            "articles": {"cardinality": {"field": "article_id"}},
        },
    })
    return {
        "chunks": count,
        "articles": agg["aggregations"]["articles"]["value"],
        "sources": {
            b["key"]: b["doc_count"]
            for b in agg["aggregations"]["sources"]["buckets"]
        },
    }
