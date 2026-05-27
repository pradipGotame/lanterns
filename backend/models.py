"""
models.py
=========
All Pydantic models used across routers and services.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ── Health ───────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status:     str
    message:    str
    upload_dir: str
    timestamp:  str


# ── Projects ─────────────────────────────────────────────────────────────────

class FileInfo(BaseModel):
    field_name:    str
    original_name: str
    size_bytes:    int
    content_type:  str
    saved_as:      str


class RunStats(BaseModel):
    requirement_files: int = Field(ge=0)
    test_files:        int = Field(ge=0)
    code_files:        int = Field(ge=0)
    total_files:       int = Field(ge=0)


class StartResponse(BaseModel):
    success:         bool
    message:         str
    project_name:    str
    project_id:      str
    started_at:      str
    stats:           RunStats
    files:           list[FileInfo]
    saved_to:        str
    pipeline:        dict[str, Any]
    atu_output_file: str
    report:          dict[str, Any] = Field(default_factory=dict)


class ProjectSummary(BaseModel):
    project_id:  str
    file_count:  int
    size_bytes:  int
    modified_at: str


class ProjectFileEntry(BaseModel):
    name:        str
    size_bytes:  int
    category:    str
    modified_at: str


# ── FileUploader ─────────────────────────────────────────────────────────────

class UploadedFileMeta(BaseModel):
    id:            str
    name:          str
    category:      str       # "requirement" | "test" | "source"
    size_bytes:    int
    uploaded_at:   str
    chunk_count:   int
    chunk_size:    int
    chunk_overlap: int


class UploadedFileDetail(UploadedFileMeta):
    chunks: list[dict]       # [{"index": int, "text": str}, ...]
