"""
chunker.py
==========
Text chunking for requirement, test, and source-code files using
LangChain's RecursiveCharacterTextSplitter.

Each category gets tuned chunk_size / chunk_overlap values:
  - requirement  : smaller chunks — precise, clause-level splits
  - test         : medium chunks  — keeps test method bodies together
  - source       : larger chunks  — preserves function / class context

For test and source categories, the splitter is chosen based on the file
extension so that language-appropriate separators are used automatically.
Supported languages and their extensions:

  C          : .c, .h
  C++        : .cpp, .cc, .cxx, .hpp
  Python     : .py
  Java       : .java
  JavaScript : .js, .mjs, .cjs
  TypeScript : .ts, .tsx
  Go         : .go
  Rust       : .rs
  Ruby       : .rb
  Kotlin     : .kt, .kts
  Swift      : .swift

Files with unrecognised extensions fall back to generic newline-based splitting.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Literal

from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from chunking_constants import (
    ASCII_OR_MARKDOWN_TABLE_RE,
    EXT_TO_LANGUAGE,
    FALLBACK_SEPARATORS,
    FALLBACK_SOURCE_CODE_SEPARATORS,
    FALLBACK_TEST_SEPARATORS,
    PLAIN_PROSE_SEPARATORS,
    PROSE_CATEGORIES,
    PROSE_EXTENSIONS,
    PROSE_RECORD_START_RE as PROSE_RECORD_START_RE_STR,
    SOURCE_CODE_SEPARATORS_BY_LANGUAGE,
    TABLE_PROSE_SEPARATORS,
    TEST_SEPARATORS_BY_LANGUAGE,
)

# ---------------------------------------------------------------------------
# Category type
# ---------------------------------------------------------------------------

Category = Literal["requirement", "test", "source"]

# ---------------------------------------------------------------------------
# Per-category splitter configs (chunk_size / chunk_overlap only)
# ---------------------------------------------------------------------------

_CONFIGS: dict[str, dict] = {
    "requirement": {
        "chunk_size": 500,
        "chunk_overlap": 50,
    },
    "test": {
        "chunk_size": 800,
        "chunk_overlap": 80,
    },
    "source": {
        "chunk_size": 1200,
        "chunk_overlap": 150,
    },
}

# ---------------------------------------------------------------------------
# Imported constants (aliases for existing local naming)
# ---------------------------------------------------------------------------

_EXT_TO_LANGUAGE = EXT_TO_LANGUAGE
_PROSE_CATEGORIES = PROSE_CATEGORIES
_PROSE_EXTENSIONS = PROSE_EXTENSIONS
_FALLBACK_SEPARATORS = FALLBACK_SEPARATORS
_TABLE_PROSE_SEPARATORS = TABLE_PROSE_SEPARATORS
_PLAIN_PROSE_SEPARATORS = PLAIN_PROSE_SEPARATORS
_ASCII_OR_MARKDOWN_TABLE_PATTERN = re.compile(ASCII_OR_MARKDOWN_TABLE_RE)
_PROSE_RECORD_START_RE = re.compile(PROSE_RECORD_START_RE_STR, re.IGNORECASE)
_TABLE_CAPTION_LINE_RE = re.compile(
    r"^\s*(?:table|tbl|caption|note|source|fig|figure)\b",
    re.IGNORECASE,
)
_TABLE_HEADING_LINE_RE = re.compile(
    r"^\s*(?:#{1,6}\s+.+|\d+(?:\.\d+)*\s+\S.+|(?:table|fig|figure|section)\s*\d+.*)$",
    re.IGNORECASE,
)
_ASCII_TABLE_BORDER_RE = re.compile(r"^\s*\+[+\-=:\s]+\+\s*$")
_ASCII_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_MARKDOWN_TABLE_ROW_RE = re.compile(r"^\s*\|.+\|\s*$")
_MARKDOWN_TABLE_ALIGN_RE = re.compile(
    r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$"
)
_NON_STRUCTURAL_ANCHOR_PREFIXES = (
    "assert",
    "expect",
    "return",
    "cu_assert",
    "t.error",
    "t.fatal",
    "t.run(",
)
_DEPTH1_TEST_ANCHOR_PREFIXES = (
    "@test",
    "@parameterizedtest",
    "def test_",
    "async def test_",
    "it(",
    "test(",
    "describe(",
    "context(",
    "func test",
    "func test",
    "testcase",
    "#[test]",
    "#[tokio::test]",
)
_WEAK_TYPE_ANCHOR_RE = re.compile(
    r"^(?:const\s+)?(?:unsigned\s+|signed\s+)?(?:void|char|short|int|long|float|double|bool|size_t)$",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_prose_mode(category: str, file_ext: str | None) -> bool:
    """Return True when the file should use prose-style splitting."""
    normalized_ext = file_ext.lower() if file_ext else None
    return (
        category in _PROSE_CATEGORIES
        or normalized_ext is None
        or normalized_ext in _PROSE_EXTENSIONS
    )


def _is_effective_prose_mode(category: str, file_ext: str | None) -> bool:
    """
    Decide prose mode with category-specific overrides.

    For tests: prose mode is only for known prose extensions.
    Otherwise, test inputs use the test splitter path.
    """
    normalized_ext = file_ext.lower() if file_ext else None
    if category == "test":
        return normalized_ext in _PROSE_EXTENSIONS
    return _is_prose_mode(category, normalized_ext)


def _language_for_ext(file_ext: str | None) -> Language | None:
    if not file_ext:
        return None
    return _EXT_TO_LANGUAGE.get(file_ext.lower())


def _language_separators_for_ext(
    file_ext: str | None,
    fallback: list[str],
    explicit_map: dict[Language, list[str]],
) -> list[str]:
    """
    Resolve separators via explicit local map first, then LangChain fallback.
    """
    lang = _language_for_ext(file_ext)
    if lang is None:
        return fallback
    explicit = explicit_map.get(lang)
    if explicit:
        return explicit
    try:
        return RecursiveCharacterTextSplitter.get_separators_for_language(lang)
    except Exception:
        return fallback


def _splitter_from_language_or_fallback(
    file_ext: str | None,
    *,
    chunk_size: int,
    chunk_overlap: int,
    fallback_separators: list[str],
    explicit_map: dict[Language, list[str]],
) -> RecursiveCharacterTextSplitter:
    """
    Build splitter from explicit separators first, with language fallback support.
    """
    separators = _language_separators_for_ext(
        file_ext, fallback_separators, explicit_map)
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators,
        length_function=len,
        is_separator_regex=False,
    )


def _test_separators_for_ext(file_ext: str | None) -> list[str]:
    return _language_separators_for_ext(
        file_ext,
        FALLBACK_TEST_SEPARATORS,
        TEST_SEPARATORS_BY_LANGUAGE,
    )


def _source_separators_for_ext(file_ext: str | None) -> list[str]:
    return _language_separators_for_ext(
        file_ext,
        FALLBACK_SOURCE_CODE_SEPARATORS,
        SOURCE_CODE_SEPARATORS_BY_LANGUAGE,
    )


def _prose_separators_for_text(text: str) -> list[str]:
    """
    Pick prose separators based on whether text contains ASCII/Markdown tables.
    """
    if _has_table_block(text):
        return _TABLE_PROSE_SEPARATORS
    return _PLAIN_PROSE_SEPARATORS


def _split_non_table_prose_records(text: str) -> list[str]:
    """
    Split prose text without special table handling.
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")

    chunks: list[str] = []
    current: list[str] = []
    found_markers = False

    for raw_line in lines:
        line = raw_line.rstrip()
        if _PROSE_RECORD_START_RE.match(line):
            found_markers = True
            if current:
                chunk = "\n".join(current).strip()
                if chunk:
                    chunks.append(chunk)
            current = [line.strip()]
            continue

        if not line.strip():
            if current:
                chunk = "\n".join(current).strip()
                if chunk:
                    chunks.append(chunk)
                current = []
            continue

        if current:
            current.append(line)

    if current:
        chunk = "\n".join(current).strip()
        if chunk:
            chunks.append(chunk)

    if found_markers and chunks:
        return chunks

    paragraphs = [p.strip() for p in re.split(
        r"\n\s*\n+", normalized) if p.strip()]
    if len(paragraphs) > 1:
        return paragraphs

    single_lines = [ln.strip() for ln in normalized.split("\n") if ln.strip()]
    return single_lines


def _anchor_tokens_from_separators(separators: list[str]) -> list[str]:
    """
    Build structural anchor tokens from language-aware separators.

    We only keep newline-led separators that look like block boundaries and
    avoid assertion/statement markers that would fragment function bodies.
    """
    anchors: list[str] = []
    seen: set[str] = set()
    for separator in separators:
        if not separator.startswith("\n"):
            continue
        if separator in {"\n", "\n\n"}:
            continue

        token = separator[1:]
        normalized = token.strip()
        if not normalized or len(normalized) < 3:
            continue
        if normalized in {";", ",", ".", "{", "}"}:
            continue

        lowered = normalized.lower()
        if any(lowered.startswith(prefix) for prefix in _NON_STRUCTURAL_ANCHOR_PREFIXES):
            continue
        if _WEAK_TYPE_ANCHOR_RE.fullmatch(lowered):
            continue

        if token not in seen:
            seen.add(token)
            anchors.append(token)

    anchors.sort(key=len, reverse=True)
    return anchors


def _line_bounds_with_depth(segment: str) -> list[tuple[int, int, int, str]]:
    """
    Return [(start, end, brace_depth_at_line_start, line_text), ...].
    """
    bounds: list[tuple[int, int, int, str]] = []
    pos = 0
    depth = 0
    for line in segment.splitlines(keepends=True):
        nxt = pos + len(line)
        bounds.append((pos, nxt, max(depth, 0), line))
        for ch in line:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth = max(0, depth - 1)
        pos = nxt

    if not bounds and segment:
        bounds.append((0, len(segment), 0, segment))
    return bounds


def _allow_depth_one_anchor(category: str, token: str) -> bool:
    """
    Permit depth=1 anchors only for well-known test starters.
    """
    if category != "test":
        return False
    lowered = token.strip().lower()
    return any(lowered.startswith(prefix) for prefix in _DEPTH1_TEST_ANCHOR_PREFIXES)


def _split_code_records(text: str, category: str, separators: list[str]) -> list[str]:
    """
    Structure-first splitting for code-like content.

    1) Detect likely declaration/test anchors from separators.
    2) Split on line starts that match anchors, respecting brace depth.
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    anchors = _anchor_tokens_from_separators(separators)
    if not anchors:
        return []

    starts: list[int] = [0]
    for start, _, depth, line in _line_bounds_with_depth(normalized):
        stripped = line.lstrip()
        if not stripped:
            continue

        matched_token: str | None = None
        for token in anchors:
            if stripped.startswith(token):
                matched_token = token
                break
        if matched_token is None:
            continue

        if depth == 0 or (depth == 1 and _allow_depth_one_anchor(category, matched_token)):
            starts.append(start)

    split_points = sorted(set(starts))
    if len(split_points) <= 1:
        return []

    records: list[str] = []
    for idx, block_start in enumerate(split_points):
        block_end = split_points[idx + 1] if idx + \
            1 < len(split_points) else len(normalized)
        block = normalized[block_start:block_end].strip()
        if block:
            records.append(block)
    return records


def _normalize_compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _drop_tiny_overlap_artifacts(chunks: list[str], chunk_size: int) -> list[str]:
    """
    Remove tiny overlap-only fragments that are fully contained in neighbors.
    """
    if len(chunks) <= 1:
        return [chunk.strip() for chunk in chunks if chunk.strip()]

    min_len = max(80, int(chunk_size * 0.25))
    cleaned: list[str] = []

    for idx, raw in enumerate(chunks):
        chunk = raw.strip()
        if not chunk:
            continue

        compact = _normalize_compact(chunk)
        next_compact = ""
        if idx + 1 < len(chunks):
            next_compact = _normalize_compact(chunks[idx + 1])

        if len(chunk) < min_len and compact:
            prev_compact = _normalize_compact(cleaned[-1]) if cleaned else ""
            if (prev_compact and compact in prev_compact) or (
                next_compact and compact in next_compact
            ):
                continue

        if cleaned and compact == _normalize_compact(cleaned[-1]):
            continue

        cleaned.append(chunk)

    return cleaned


def _find_table_spans(text: str) -> list[tuple[int, int]]:
    """
    Find table spans as (start_char, end_char) using line-wise detection.
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    line_bounds = _line_bounds(normalized)
    line_texts = [line.rstrip("\n") for _, _, line in line_bounds]
    spans: list[tuple[int, int]] = []

    i = 0
    n = len(line_texts)
    while i < n:
        # ASCII table: border + rows/borders block
        if _ASCII_TABLE_BORDER_RE.match(line_texts[i]):
            j = i + 1
            has_row = False
            while j < n and (
                _ASCII_TABLE_BORDER_RE.match(line_texts[j])
                or _ASCII_TABLE_ROW_RE.match(line_texts[j])
            ):
                if _ASCII_TABLE_ROW_RE.match(line_texts[j]):
                    has_row = True
                j += 1
            if has_row and (j - i) >= 3:
                spans.append((line_bounds[i][0], line_bounds[j - 1][1]))
                i = j
                continue

        # Markdown table: header row + alignment row + optional body rows
        if (
            i + 1 < n
            and _MARKDOWN_TABLE_ROW_RE.match(line_texts[i])
            and _MARKDOWN_TABLE_ALIGN_RE.match(line_texts[i + 1])
        ):
            j = i + 2
            while j < n and _MARKDOWN_TABLE_ROW_RE.match(line_texts[j]):
                j += 1
            spans.append((line_bounds[i][0], line_bounds[j - 1][1]))
            i = j
            continue

        i += 1

    return spans


def _has_table_block(text: str) -> bool:
    """
    Detect table presence:
    1) regex gate (fast fail),
    2) line-wise detection (precise spans).
    """
    if not _ASCII_OR_MARKDOWN_TABLE_PATTERN.search(text or ""):
        return False
    return bool(_find_table_spans(text or ""))


def _line_bounds(segment: str) -> list[tuple[int, int, str]]:
    """
    Return [(start, end, line_text_with_newline_if_any), ...] for a text segment.
    """
    bounds: list[tuple[int, int, str]] = []
    pos = 0
    for line in segment.splitlines(keepends=True):
        nxt = pos + len(line)
        bounds.append((pos, nxt, line))
        pos = nxt
    if not bounds and segment:
        bounds.append((0, len(segment), segment))
    return bounds


def _find_heading_start(prefix: str) -> int | None:
    """
    Find heading line start (relative to prefix) to attach above a table.
    """
    for start, _, line in reversed(_line_bounds(prefix)):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.endswith(":") or _TABLE_HEADING_LINE_RE.match(stripped):
            return start
        return None
    return None


def _find_caption_end(suffix: str) -> int | None:
    """
    Find caption line end (relative to suffix) to attach below a table.
    """
    for _, end, line in _line_bounds(suffix):
        stripped = line.strip()
        if not stripped:
            continue
        if _TABLE_CAPTION_LINE_RE.match(stripped):
            return end
        return None
    return None


def _make_splitter(
    category: str,
    file_ext: str | None = None,
    text: str | None = None,
) -> RecursiveCharacterTextSplitter:
    """
    Build the right splitter for *category* and optional *file_ext*.

    - requirement  → always prose splitter (paragraph / sentence breaks)
    - test/source  → language-aware splitter when extension is recognised,
                     generic fallback otherwise
    """
    cfg = _CONFIGS.get(category, _CONFIGS["source"])
    size = cfg["chunk_size"]
    overlap = cfg["chunk_overlap"]

    normalized_ext = file_ext.lower() if file_ext else None
    if category == "test":
        if _is_effective_prose_mode(category, normalized_ext):
            prose_separators = _prose_separators_for_text(text or "")
            return RecursiveCharacterTextSplitter(
                chunk_size=size,
                chunk_overlap=overlap,
                separators=prose_separators,
                length_function=len,
                is_separator_regex=False,
            )
        return _splitter_from_language_or_fallback(
            normalized_ext,
            chunk_size=size,
            chunk_overlap=overlap,
            fallback_separators=FALLBACK_TEST_SEPARATORS,
            explicit_map=TEST_SEPARATORS_BY_LANGUAGE,
        )
    if category == "source":
        return _splitter_from_language_or_fallback(
            normalized_ext,
            chunk_size=size,
            chunk_overlap=overlap,
            fallback_separators=FALLBACK_SOURCE_CODE_SEPARATORS,
            explicit_map=SOURCE_CODE_SEPARATORS_BY_LANGUAGE,
        )

    if _is_effective_prose_mode(category, normalized_ext):
        # Prose / no extension info → use fixed separator list
        prose_separators = _prose_separators_for_text(text or "")
        return RecursiveCharacterTextSplitter(
            chunk_size=size,
            chunk_overlap=overlap,
            separators=prose_separators,
            length_function=len,
            is_separator_regex=False,
        )

    # Unknown extension — generic newline-based fallback
    return RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        separators=_FALLBACK_SEPARATORS,
        length_function=len,
        is_separator_regex=False,
    )


def _split_prose_records(text: str) -> list[str]:
    """
    Split non-code prose text into logical records.

    Strategy:
    1) If lines start with record markers (e.g., RQ100, TC12, 1.), keep each
       marker-led block together.
    2) Else split by blank-line paragraphs.
    3) Else split by non-empty lines.
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not _ASCII_OR_MARKDOWN_TABLE_PATTERN.search(normalized):
        return _split_non_table_prose_records(normalized)
    table_spans = _find_table_spans(normalized)
    if not table_spans:
        return _split_non_table_prose_records(normalized)

    records: list[str] = []
    cursor = 0

    for idx, (table_start, table_end) in enumerate(table_spans):
        if table_end <= table_start:
            continue

        next_start = table_spans[idx + 1][0] if idx + \
            1 < len(table_spans) else len(normalized)

        prefix = normalized[cursor:table_start]
        heading_rel_start = _find_heading_start(prefix)
        heading_abs_start = (
            cursor + heading_rel_start) if heading_rel_start is not None else table_start
        heading_abs_start = max(heading_abs_start, cursor)

        before_table = normalized[cursor:heading_abs_start].strip()
        if before_table:
            records.extend(_split_non_table_prose_records(before_table))

        suffix = normalized[table_end:next_start]
        caption_rel_end = _find_caption_end(suffix)
        block_end = table_end + (caption_rel_end or 0)

        table_block = normalized[heading_abs_start:block_end].strip()
        if table_block:
            records.append(table_block)

        cursor = block_end

    tail = normalized[cursor:].strip()
    if tail:
        records.extend(_split_non_table_prose_records(tail))

    return records


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def chunk_text(
    text: str,
    category: str,
    file_path: str | Path | None = None,
) -> list[dict]:
    """
    Split *text* into overlapping chunks appropriate for *category*.

    Parameters
    ----------
    text      : raw file content as a string
    category  : "requirement", "test", or "source"
    file_path : optional path or filename — used to detect file extension
                and select the correct language-aware splitter for
                test/source categories

    Returns
    -------
    A list of dicts: [{"index": 0, "text": "..."}, ...]
    """
    ext = Path(file_path).suffix.lower() if file_path else None

    if _is_effective_prose_mode(category, ext):
        prose_records = _split_prose_records(text)
        if prose_records:
            cfg = _CONFIGS.get(category, _CONFIGS["source"])
            prose_separators = _prose_separators_for_text(text)
            prose_splitter = RecursiveCharacterTextSplitter(
                chunk_size=cfg["chunk_size"],
                chunk_overlap=cfg["chunk_overlap"],
                separators=prose_separators,
                length_function=len,
                is_separator_regex=False,
            )
            raw_chunks: list[str] = []
            for record in prose_records:
                # Keep detected table blocks atomic with their attached heading/caption.
                if _has_table_block(record):
                    raw_chunks.append(record)
                elif len(record) <= cfg["chunk_size"]:
                    raw_chunks.append(record)
                else:
                    raw_chunks.extend(prose_splitter.split_text(record))
            return [{"index": i, "text": chunk} for i, chunk in enumerate(raw_chunks)]

    if category == "test":
        cfg = _CONFIGS.get(category, _CONFIGS["source"])
        separators = _test_separators_for_ext(ext)
        code_records = _split_code_records(text, category, separators)
        if code_records:
            splitter = _splitter_from_language_or_fallback(
                ext,
                chunk_size=cfg["chunk_size"],
                chunk_overlap=cfg["chunk_overlap"],
                fallback_separators=FALLBACK_TEST_SEPARATORS,
                explicit_map=TEST_SEPARATORS_BY_LANGUAGE,
            )
            raw_chunks: list[str] = []
            for record in code_records:
                if len(record) <= cfg["chunk_size"]:
                    raw_chunks.append(record)
                else:
                    raw_chunks.extend(splitter.split_text(record))
            raw_chunks = _drop_tiny_overlap_artifacts(
                raw_chunks, cfg["chunk_size"])
            return [{"index": i, "text": chunk} for i, chunk in enumerate(raw_chunks)]

    if category == "source":
        cfg = _CONFIGS.get(category, _CONFIGS["source"])
        separators = _source_separators_for_ext(ext)
        code_records = _split_code_records(text, category, separators)
        if code_records:
            splitter = _splitter_from_language_or_fallback(
                ext,
                chunk_size=cfg["chunk_size"],
                chunk_overlap=cfg["chunk_overlap"],
                fallback_separators=FALLBACK_SOURCE_CODE_SEPARATORS,
                explicit_map=SOURCE_CODE_SEPARATORS_BY_LANGUAGE,
            )
            raw_chunks: list[str] = []
            for record in code_records:
                if len(record) <= cfg["chunk_size"]:
                    raw_chunks.append(record)
                else:
                    raw_chunks.extend(splitter.split_text(record))
            raw_chunks = _drop_tiny_overlap_artifacts(
                raw_chunks, cfg["chunk_size"])
            return [{"index": i, "text": chunk} for i, chunk in enumerate(raw_chunks)]

    splitter = _make_splitter(category, ext, text=text)
    raw_chunks = splitter.split_text(text)
    return [{"index": i, "text": chunk} for i, chunk in enumerate(raw_chunks)]


def chunk_bytes(
    content: bytes,
    category: str,
    file_path: str | Path | None = None,
    encoding: str = "utf-8",
) -> list[dict]:
    """Convenience wrapper that decodes bytes before chunking."""
    text = content.decode(encoding, errors="replace")
    return chunk_text(text, category, file_path=file_path)


def get_chunk_config(category: str) -> dict:
    """Return the splitter config for a given category (for logging/display)."""
    return dict(_CONFIGS.get(category, _CONFIGS["source"]))


def get_language(file_path: str | Path) -> Language | None:
    """Return the detected LangChain Language for a file, or None if unknown."""
    ext = Path(file_path).suffix.lower()
    return _EXT_TO_LANGUAGE.get(ext)
