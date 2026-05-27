"""
main.py
=======
FastAPI application entry point.

Responsibilities (only):
  1. Create the FastAPI app
  2. Register CORS middleware
  3. Include all routers

All business logic lives in routers/ and services/.

Run:
    uvicorn main:app --reload --port 8000

Docs:
    http://localhost:8000/docs
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import embed, files, health, projects, trace

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Multi-Agent System API",
    description=(
        "Backend for the thesis multi-agent traceability system.\n\n"
        "**Routers**\n"
        "- `/health` — liveness check\n"
        "- `/api/files/*` — FileUploader (persistent chunked file store)\n"
        "- `/api/projects/*` — Project management + Phase 1/2/3 pipeline\n"
        "- `/api/embed/*` — OpenAI embedding + Chroma vector store\n"
        "- `/api/trace/*` — Traceability retrieval (dense recall + FlashRank rerank)\n"
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(health.router)
app.include_router(files.router)
app.include_router(projects.router)
app.include_router(embed.router)
app.include_router(trace.router)

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
