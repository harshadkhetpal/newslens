#!/usr/bin/env python3
"""CLI ingestion: crawl default feeds and index new articles."""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

from newslens import crawler, indexer  # noqa: E402

def main(per_feed: int = 10) -> None:
    cl = indexer.client()
    indexer.ensure_index(cl)
    new, skipped = 0, 0
    for article in crawler.crawl(per_feed=per_feed):
        if indexer.already_indexed(article.id, cl):
            skipped += 1
            continue
        n = indexer.index_article(article, cl)
        if n:
            new += 1
            print(f"  indexed [{n:>2} chunks] {article.title[:70]}")
    print(f"\ndone: {new} new articles, {skipped} already indexed")
    print(indexer.stats(cl))

if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
