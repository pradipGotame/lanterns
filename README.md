# Closing the Semantic Gap: Automated Test Suite Management using Multi-Agent Systems

## Purpose

This repository contains the implementation for a thesis project on multi-agent support for software traceability workflows.

The system helps analyze relationships between:

- software requirements
- test cases
- source code

It includes:

- a React + TypeScript + Vite frontend
- a FastAPI backend
- file upload and chunking
- OpenAI-based embedding
- vector search with Chroma
- reranking and traceability analysis
- assertion analysis
- generated-test output

The main shipped workflow is the corpus-wide frontend flow in `src/FileUploader.tsx`, backed by:

- `/api/files`
- `/api/embed`
- `/api/trace`
- `/health`

The backend also includes a separate project-scoped workflow under `/api/projects`.

## How To Run

### Prerequisites

- Node.js 18+ and npm
- Python 3.10+ or newer
- An OpenAI API key

### 1. Configure Environment Variables

Create a frontend environment file from the example:

```bash
cp .env.example .env
```

Create a backend environment file from the example:

```bash
cp backend/.env.example backend/.env
```

Then edit `backend/.env` and set:

```bash
OPENAI_API_KEY=your_real_api_key_here
OPENAI_BASE_URL=your_llm_base_url_here
OPENAI_EMBEDDING_MODEL=your_embedding_model_here
OPENAI_LLM_MODEL=your_llm_model_here
```

The default local frontend API URL is:

```bash
VITE_API_BASE=http://localhost:8000
```

### 2. Install And Run The Frontend

From the repository root:

```bash
npm install
npm run dev
```

Vite will print the local frontend URL, usually:

```bash
http://localhost:5173
```

### 3. Install And Run The Backend

From the repository root:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Alternatively, from the repository root after installing backend dependencies:

```bash
backend/.venv/bin/python -m uvicorn main:app --app-dir backend --reload --port 8000
```

The backend health check is available at:

```bash
http://localhost:8000/health
```

## What Is Needed For Direct Execution

The application can run locally, but several features require external services or local runtime state.

Required:

- A valid OpenAI API key in `backend/.env`
- Network access to OpenAI APIs for embedding and LLM-based analysis
- Python dependencies from `backend/requirements.txt`
- Node dependencies from `package.json`

### LLM Provider Support

The project currently uses OpenAI-compatible APIs for both embeddings and LLM-based reasoning.

By default, it expects:

- `OPENAI_API_KEY`
- `OPENAI_EMBEDDING_MODEL`
- `OPENAI_LLM_MODEL`

Other providers such as Claude or Gemini are not drop-in replacements in the current codebase unless they are exposed through an OpenAI-compatible API gateway.

To use Claude, Gemini, or another native provider directly, the embedding and LLM client layers would need to be adapted. The vector index should also be rebuilt if the embedding model or embedding provider changes, because vectors from different embedding models are generally not compatible.

### LangChain Usage

This project uses open-source LangChain Python packages as local libraries for text splitting, OpenAI embeddings, document wrappers, and reranker integration.

It does not require LangChain Cloud or LangSmith to run. No LangChain Cloud or LangSmith API key is needed by default.

LangChain Cloud or LangSmith may have separate costs if you choose to enable hosted tracing, monitoring, or deployment features, but those services are not part of the default local setup for this repository.

Generated or local-only data is intentionally not committed:

- uploaded files
- vector indexes
- Chroma data
- traceability reports
- generated tests
- local `.env` files
- Python virtual environments

These files are recreated while using the system.

If the project was originally run with private or institution-specific infrastructure, that infrastructure is not included in this repository. To reproduce those runs exactly, you would need the same private datasets, credentials, API access, and any unpublished execution environment used during the original experiments.

Without those private pieces, the repository still provides the source code and local workflow, but exact experimental outputs may differ.

## Repository Structure

```text
.
├── src/                     # Frontend app
├── public/                  # Static assets
├── backend/                 # FastAPI backend and pipeline services
│   ├── routers/             # API route handlers
│   ├── services/            # Retrieval and embedding services
│   └── scripts/             # Experiment/support scripts
├── .env.example             # Sample frontend environment file
├── backend/.env.example     # Sample backend environment file
├── IMPLEMENTATION.md        # Detailed implementation notes
└── README.md
```

## Public Release Notes

Before publishing or archiving this repository, verify that no real secrets or private data are tracked by Git.

Do not commit:

- `.env`
- `backend/.env`
- API keys
- tokens
- uploaded private files
- generated traceability artifacts containing private data
