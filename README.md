# GitHub AI Help

A full-stack **AI Software Engineering Agent** that can import a Git repository, inspect the codebase, index code, answer repository questions, plan changes, generate patches, request user approval, apply changes, run tests in an isolated Docker sandbox, and retry based on test failures.

## Stack
- Frontend: React, TypeScript, Vite, Tailwind CSS, TanStack Query, React Router, Monaco Editor
- Backend: FastAPI, Pydantic, SQLAlchemy, PostgreSQL, pgvector, Redis
- Auth: JWT access + refresh tokens, bcrypt password hashing
- Git: GitPython
- AI/Retrieval: pluggable LLM provider, AST-aware chunking, embeddings interface, pgvector storage, hybrid retrieval hooks
- Execution: Docker sandbox with CPU/memory/time limits
- Tests: pytest, Vitest, React Testing Library

## Quick start with Docker

```bash
cp .env.example .env
docker compose up --build
```

Frontend: http://localhost:5173
Backend: http://localhost:8000
API docs: http://localhost:8000/docs

## Main workflow
1. Register/login.
2. Import a repository by URL.
3. Browse repository files.
4. Index code into semantic chunks.
5. Create a coding task.
6. Agent retrieves relevant code and generates a plan.
7. Agent proposes file changes and a Git diff.
8. User approves or rejects the patch.
9. Approved patches are applied on a temporary branch.
10. Tests run in an isolated Docker container.
11. Failures are captured and stored for a retry loop.
12. Final report includes changed files, diff, tests, and execution history.

## Notes
The project includes a deterministic fallback provider so the app can run without an external LLM key. Configure an external provider by implementing `BaseLLMProvider` in `backend/app/agents/providers.py`.

## Production deployment

Recommended deployment split:

- **Frontend:** Vercel (`frontend/`)
- **Backend:** Railway (`backend/`)
- **Database:** Supabase PostgreSQL + pgvector
- **LLM gateway:** OpenRouter

### Backend environment variables

Configure these on Railway:

- `ENV=production`
- `SECRET_KEY`
- `DATABASE_URL`
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`
- `CORS_ORIGINS`
- `REPO_STORAGE_PATH`
- `TEST_EXECUTION_MODE`

The production backend starts with:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Frontend environment variables

Configure on Vercel:

- `VITE_API_URL=https://<backend-domain>/api/v1`

`frontend/vercel.json` provides the SPA fallback required for React Router.

> Never commit `.env`, database credentials, API keys, or JWT secrets.
