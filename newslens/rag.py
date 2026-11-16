"""Answer generation over retrieved chunks.

With ANTHROPIC_API_KEY set, answers come from Claude with inline [n]
citations. Without a key the system degrades gracefully to an extractive
mode (top passages, still cited) so the demo never shows an error state.
"""

from typing import Any, Dict, List

from . import config, indexer

SYSTEM = (
    "You are NewsLens, a news research assistant. Answer the question using "
    "ONLY the numbered source passages provided. Cite passages inline as [n]. "
    "If the sources do not contain the answer, say so plainly. Keep answers "
    "under 200 words, neutral in tone."
)


def _context_block(hits: List[Dict[str, Any]]) -> str:
    lines = []
    for i, h in enumerate(hits, 1):
        lines.append(
            f"[{i}] {h['title']} — {h['source']}\n{h['text'][:1200]}"
        )
    return "\n\n".join(lines)


def _extractive_answer(question: str, hits: List[Dict[str, Any]]) -> str:
    top = hits[:3]
    parts = [
        "(extractive mode — set ANTHROPIC_API_KEY for synthesised answers)\n"
    ]
    for i, h in enumerate(top, 1):
        parts.append(f"[{i}] {h['title']} ({h['source']}): {h['text'][:300]}…")
    return "\n\n".join(parts)


def answer(question: str, k: int = 6) -> Dict[str, Any]:
    hits = indexer.hybrid_search(question, k=k)
    if not hits:
        return {"answer": "The index is empty — run an ingest first.",
                "sources": []}

    sources = [
        {"n": i, "title": h["title"], "url": h["url"],
         "source": h["source"], "published": h.get("published")}
        for i, h in enumerate(hits, 1)
    ]

    if not config.ANTHROPIC_API_KEY:
        return {"answer": _extractive_answer(question, hits),
                "sources": sources, "mode": "extractive"}

    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=config.ANSWER_MODEL,
        max_tokens=600,
        system=SYSTEM,
        messages=[{
            "role": "user",
            "content": (
                f"Question: {question}\n\nSource passages:\n\n"
                + _context_block(hits)
            ),
        }],
    )
    return {
        "answer": "".join(
            b.text for b in message.content if b.type == "text"
        ),
        "sources": sources,
        "mode": "llm",
    }
