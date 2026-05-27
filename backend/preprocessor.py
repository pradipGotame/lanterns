"""
preprocessor.py  —  Phase 1 ATU Extraction
===========================================
Extracts Atomic Traceability Units (ATUs) from uploaded project files.

ATU granularity strategy
-------------------------
  requirement files → paragraph / numbered-item splitting
  test files        → Python: AST function extraction; others: fixed-stride chunks
  source/code files → Python: AST function+class extraction; others: fixed-stride chunks
  PDF files         → page-level text extraction (requires pypdf)

Category mapping (from filename prefix → ATU category)
-------------------------------------------------------
  requirement_*  →  "requirement"
  test_*         →  "test"
  code_*         →  "source"   ← Phase 3 searches for category="source"
  (other)        →  "source"
"""

from __future__ import annotations

import ast
import re
import warnings
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


# ── ATU models ───────────────────────────────────────────────────────────────

class HierarchyStatus(str, Enum):
    Leaf     = "Leaf"
    Umbrella = "Umbrella"


class ATU(BaseModel):
    id:               str
    text:             str
    source_file:      str
    category:         str           # "requirement" | "test" | "source"
    hierarchy_status: HierarchyStatus = HierarchyStatus.Leaf
    metadata:         dict[str, Any] = Field(default_factory=dict)


class PipelineResult(BaseModel):
    project_id:       str
    total_artifacts:  int = 0
    total_atus:       int = 0
    requirements:     list[ATU] = Field(default_factory=list)
    tests:            list[ATU] = Field(default_factory=list)
    sources:          list[ATU] = Field(default_factory=list)
    warnings:         list[str] = Field(default_factory=list)


# ── Constants ─────────────────────────────────────────────────────────────────

_TEXT_EXTS  = {".txt", ".md", ".rst", ".text", ".markdown"}
_PY_EXT     = {".py"}
_CODE_EXTS  = {".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".h",
               ".cs", ".go", ".rb", ".php", ".swift", ".kt", ".rs", ".scala"}
_PDF_EXT    = {".pdf"}

_MIN_WORDS      = 6       # minimum words for a chunk to be kept
_MAX_CHARS      = 3000    # hard cap per ATU text
_STRIDE_LINES   = 40      # lines per fixed-stride chunk (non-Python code)
_OVERLAP_LINES  = 10      # line overlap between adjacent chunks


# ── Category detection ────────────────────────────────────────────────────────

def _file_category(filename: str) -> str:
    """
    Infer ATU category from the saved filename prefix.

    project.py saves files as  {category}_{timestamp}_{original}.
    'code' maps to 'source' because Phase 3 searches for category='source'.
    """
    name = filename.lower()
    if name.startswith("requirement"):
        return "requirement"
    if name.startswith("test"):
        return "test"
    return "source"  # code_* and anything else


# ── Text helpers ──────────────────────────────────────────────────────────────

def _word_count(text: str) -> int:
    return len(text.split())


def _truncate(text: str) -> str:
    return text[:_MAX_CHARS] if len(text) > _MAX_CHARS else text


# ── Requirement / plain-text extraction ──────────────────────────────────────

_NUMBERED_ITEM = re.compile(r"^\s*(?:\d+[.)]\s+|[A-Z]\.\s+|[-*•]\s+)", re.MULTILINE)


def _extract_text_atus(
    filepath: Path,
    category: str,
    prefix: str,
) -> list[ATU]:
    """
    Split a plain-text / Markdown file into paragraph ATUs.

    Priority: numbered/bulleted items → double-newline paragraphs → single lines.
    """
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return []

    if not content:
        return []

    atus: list[ATU] = []

    # Try to split on numbered / bulleted items first
    splits = _NUMBERED_ITEM.split(content)
    if len(splits) > 3:
        # Reassemble: the split removes the delimiter, so grab the markers too
        markers = _NUMBERED_ITEM.findall(content)
        chunks = []
        for i, part in enumerate(splits):
            if i == 0 and part.strip():
                chunks.append(part.strip())
            elif i > 0 and i - 1 < len(markers):
                chunk = (markers[i - 1] + part).strip()
                if chunk:
                    chunks.append(chunk)
    else:
        # Fall back to double-newline paragraph split
        chunks = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]

    if not chunks:
        chunks = [line.strip() for line in content.splitlines() if line.strip()]

    for idx, chunk in enumerate(chunks):
        if _word_count(chunk) < _MIN_WORDS:
            continue
        atus.append(ATU(
            id=f"{prefix}_{idx:04d}",
            text=_truncate(chunk),
            source_file=filepath.name,
            category=category,
        ))

    return atus


# ── Python ATU extraction (AST) ───────────────────────────────────────────────

def _extract_python_atus(
    filepath: Path,
    category: str,
    prefix: str,
) -> list[ATU]:
    """
    Extract ATUs from a Python file using the AST.

    Granularity:
      - Top-level functions and async functions
      - Top-level classes (full class body as one ATU)
      - Methods within top-level classes (one ATU each)
    Falls back to _extract_text_atus on SyntaxError.
    """
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
        lines  = source.splitlines()
        tree   = ast.parse(source)
    except SyntaxError:
        return _extract_text_atus(filepath, category, prefix)

    atus: list[ATU] = []

    def _node_text(node: ast.AST) -> str | None:
        try:
            start = node.lineno - 1          # type: ignore[attr-defined]
            end   = node.end_lineno          # type: ignore[attr-defined]
            return "\n".join(lines[start:end]).strip()
        except Exception:
            return None

    def _add(node: ast.AST, override_id: str | None = None) -> None:
        text = _node_text(node)
        if not text or _word_count(text) < _MIN_WORDS:
            return
        atu_id = override_id or f"{prefix}_{len(atus):04d}"
        atus.append(ATU(
            id=atu_id,
            text=_truncate(text),
            source_file=filepath.name,
            category=category,
        ))

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _add(node)
        elif isinstance(node, ast.ClassDef):
            # Class as a whole
            _add(node)
            # Individual methods
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    _add(child, override_id=f"{prefix}_{len(atus):04d}")

    return atus if atus else _extract_text_atus(filepath, category, prefix)


# ── Generic code extraction (fixed-stride chunks) ────────────────────────────

def _extract_code_atus(
    filepath: Path,
    category: str,
    prefix: str,
) -> list[ATU]:
    """
    Chunk a non-Python code file into fixed-stride ATUs with line overlap.
    Stride = _STRIDE_LINES, overlap = _OVERLAP_LINES.
    """
    try:
        lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    if not lines:
        return []

    atus: list[ATU] = []
    step  = max(1, _STRIDE_LINES - _OVERLAP_LINES)
    start = 0
    idx   = 0

    while start < len(lines):
        chunk = "\n".join(lines[start : start + _STRIDE_LINES]).strip()
        if _word_count(chunk) >= _MIN_WORDS:
            atus.append(ATU(
                id=f"{prefix}_{idx:04d}",
                text=_truncate(chunk),
                source_file=filepath.name,
                category=category,
            ))
            idx += 1
        start += step

    return atus


# ── PDF extraction ────────────────────────────────────────────────────────────

def _extract_pdf_atus(
    filepath: Path,
    category: str,
    prefix: str,
) -> list[ATU]:
    """
    Extract ATUs from a PDF file.
    Uses pypdf if available; falls back to a raw-bytes latin-1 read.
    Each page becomes one ATU (pages with < _MIN_WORDS words are skipped).
    """
    try:
        import pypdf  # type: ignore
        reader = pypdf.PdfReader(str(filepath))
        atus: list[ATU] = []
        for page_idx, page in enumerate(reader.pages):
            text = (page.extract_text() or "").strip()
            if _word_count(text) < _MIN_WORDS:
                continue
            atus.append(ATU(
                id=f"{prefix}_{page_idx:04d}",
                text=_truncate(text),
                source_file=filepath.name,
                category=category,
            ))
        return atus if atus else _extract_text_atus(filepath, category, prefix)
    except ImportError:
        pass
    except Exception:
        pass

    # Fallback: try reading as latin-1 text and treat as plain text
    return _extract_text_atus(filepath, category, prefix)


# ── Per-file dispatcher ───────────────────────────────────────────────────────

def _extract_file_atus(filepath: Path, category: str, prefix: str) -> list[ATU]:
    """Route to the right extractor based on file extension."""
    ext = filepath.suffix.lower()

    if ext in _PY_EXT:
        return _extract_python_atus(filepath, category, prefix)
    if ext in _CODE_EXTS:
        return _extract_code_atus(filepath, category, prefix)
    if ext in _PDF_EXT:
        return _extract_pdf_atus(filepath, category, prefix)
    # Default: treat as plain text (covers .txt, .md, .rst, unknown extensions)
    return _extract_text_atus(filepath, category, prefix)


# ── Pipeline ──────────────────────────────────────────────────────────────────

class Phase1Pipeline:
    """
    Phase 1 ATU extraction pipeline.

    Scans the project upload directory, classifies each file by its filename
    prefix (requirement_ / test_ / code_), and dispatches to the appropriate
    extractor.  Returns a PipelineResult ready for Phase 2 indexing.
    """

    def run_from_saved_files(
        self,
        *,
        project_id: str,
        project_dir: Path,
    ) -> PipelineResult:
        """
        Extract ATUs from all files saved in *project_dir*.

        Args:
            project_id:  Unique project identifier.
            project_dir: Directory containing the uploaded files (with category
                         prefix in the filename, e.g. requirement_103045_spec.txt).

        Returns:
            PipelineResult with populated requirements / tests / sources lists.
        """
        result = PipelineResult(project_id=project_id)

        if not project_dir.exists():
            result.warnings.append(f"Project directory not found: {project_dir}")
            return result

        # Collect files, skip JSON/metadata side-cars written by the router
        skip_names = {"phase1_atus.json", "atus.json"}
        files = sorted(
            [f for f in project_dir.iterdir()
             if f.is_file() and f.name not in skip_names],
            key=lambda f: f.name,
        )

        if not files:
            result.warnings.append("No files found in project directory.")
            return result

        total_artifacts = len(files)
        req_atus: list[ATU]  = []
        test_atus: list[ATU] = []
        src_atus: list[ATU]  = []
        warn: list[str]      = []

        for filepath in files:
            category = _file_category(filepath.name)
            # Build a stable, unique prefix from project_id + filename stem
            safe_stem = re.sub(r"[^a-zA-Z0-9_]", "_", filepath.stem)[:40]
            prefix    = f"{project_id[:8]}_{safe_stem}"

            try:
                atus = _extract_file_atus(filepath, category, prefix)
            except Exception as exc:
                warn.append(f"Failed to extract ATUs from {filepath.name}: {exc}")
                continue

            if not atus:
                warn.append(f"No ATUs extracted from {filepath.name} (file may be empty or unsupported).")
                continue

            if category == "requirement":
                req_atus.extend(atus)
            elif category == "test":
                test_atus.extend(atus)
            else:
                src_atus.extend(atus)

            print(f"[Phase1] {filepath.name}: {len(atus)} ATUs ({category})")

        total_atus = len(req_atus) + len(test_atus) + len(src_atus)

        result.total_artifacts = total_artifacts
        result.total_atus      = total_atus
        result.requirements    = req_atus
        result.tests           = test_atus
        result.sources         = src_atus
        result.warnings        = warn

        print(
            f"[Phase1] {project_id}: {total_artifacts} files → "
            f"{len(req_atus)} req + {len(test_atus)} test + {len(src_atus)} source ATUs"
        )

        return result
