# API map

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`
- `GET/POST/DELETE /api/v1/repositories`
- `GET /api/v1/repositories/{id}/files`
- `GET /api/v1/repositories/{id}/file?path=...`
- `POST /api/v1/search/{id}/index`
- `GET /api/v1/search/{id}?q=...`
- `POST /api/v1/tasks`
- `POST /api/v1/agent/tasks/{task_id}/run`
- `GET /api/v1/agent/runs/{run_id}`
- `POST /api/v1/agent/runs/{run_id}/approve`
- `GET /api/v1/agent/repositories/{repo_id}/ask?q=...`
