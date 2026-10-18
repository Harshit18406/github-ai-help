# GitHub AI Help

GitHub AI Help is a full-stack AI software engineering agent that understands real repositories, answers codebase questions, generates implementation plans, proposes reviewable patches, and keeps the developer in control through an approval-first workflow.

## Live Demo

- Frontend: https://github-ai-help.vercel.app
- Backend Health: https://backend-production-5b813.up.railway.app/health

## What it can do

- Import a public Git repository
- Browse and inspect repository files
- Index code into searchable semantic chunks
- Ask questions grounded in repository context
- Generate implementation plans for coding tasks
- Propose file edits and unified Git diffs
- Require human approval before changes are applied
- Apply approved changes on an isolated Git branch
- Store agent execution history and test results
- Support retry workflows after failed test runs

## Architecture

```text
React + TypeScript frontend
        ↓
FastAPI REST API
        ↓
Repository / Agent Services
        ↓
GitPython + Code Indexer + LLM Provider
        ↓
Persistent database + repository workspace
