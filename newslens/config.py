"""Central configuration — everything overridable via environment variables."""

import os

OPENSEARCH_HOST = os.getenv("NEWSLENS_OS_HOST", "localhost")
OPENSEARCH_PORT = int(os.getenv("NEWSLENS_OS_PORT", "9200"))
INDEX_NAME = os.getenv("NEWSLENS_INDEX", "newslens-articles")

EMBEDDING_MODEL = os.getenv("NEWSLENS_EMBED_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 output dimension

CHUNK_MAX_CHARS = int(os.getenv("NEWSLENS_CHUNK_CHARS", "1400"))
CHUNK_OVERLAP_CHARS = int(os.getenv("NEWSLENS_CHUNK_OVERLAP", "200"))

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANSWER_MODEL = os.getenv("NEWSLENS_ANSWER_MODEL", "claude-sonnet-5")

# Curated, reliable RSS feeds. Deliberately conservative: public feeds that
# welcome aggregation. Extend via feeds.txt in the project root.
DEFAULT_FEEDS = [
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "https://www.theverge.com/rss/index.xml",
    "https://techcrunch.com/feed/",
    "https://hnrss.org/frontpage",
    "https://www.wired.com/feed/rss",
]

REQUEST_TIMEOUT = 20
USER_AGENT = "NewsLensBot/0.1 (+https://github.com/harshadkhetpal/newslens)"
