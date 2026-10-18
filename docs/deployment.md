# Production deployment

GitHub AI Help uses a split deployment:

- **Frontend:** Vercel, root directory `frontend`
- **Backend:** Railway, root directory `backend`
- **Database:** PostgreSQL (Supabase recommended)
- **LLM gateway:** OpenRouter

## Railway backend

Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Health check: `/health`

Production secrets must be configured in Railway rather than committed to Git:

- `SECRET_KEY`
- `DATABASE_URL`
- `OPENROUTER_API_KEY`

Other production settings are configured as Railway environment variables.

## Vercel frontend

Set the project root directory to `frontend` and configure:

```
VITE_API_URL=https://<railway-backend-domain>/api/v1
```

After the Vercel domain is assigned, add that exact origin to the Railway backend's `CORS_ORIGINS`.

## Security

Never commit `.env`, API keys, database passwords, or JWT secrets.
