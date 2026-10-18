# Architecture

```text
React UI
  -> FastAPI routes
      -> Services
          -> Repositories (SQLAlchemy/PostgreSQL)
          -> Git service (GitPython)
          -> Code intelligence (AST + embeddings + pgvector)
          -> Agent orchestrator
              -> constrained tools
              -> patch proposal
              -> approval gate
              -> Docker sandbox tests
```

The design intentionally separates HTTP, business logic, persistence, agent orchestration, code intelligence, Git, and sandbox execution.
