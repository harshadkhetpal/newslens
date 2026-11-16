"""Paragraph-aware chunking with overlap.

Chunks respect paragraph boundaries where possible so embeddings carry
coherent thoughts; a sliding overlap keeps answers that straddle a boundary
retrievable from either side.
"""

from typing import List

from . import config


def chunk_text(text: str,
               max_chars: int = config.CHUNK_MAX_CHARS,
               overlap: int = config.CHUNK_OVERLAP_CHARS) -> List[str]:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: List[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 1 <= max_chars:
            current = f"{current}\n{para}".strip()
            continue
        if current:
            chunks.append(current)
            current = current[-overlap:] if overlap else ""
        # A single paragraph longer than the window gets hard-split.
        while len(para) > max_chars:
            chunks.append((current + "\n" + para[:max_chars]).strip())
            para = para[max_chars - overlap:]
            current = ""
        current = f"{current}\n{para}".strip()
    if current:
        chunks.append(current)
    return chunks
