# TicketFlow

Event ticketing API built with FastAPI, SQLAlchemy 2, PostgreSQL and uv.

## Run
```bash
cp .env.example .env
docker compose up -d            # postgres
uv sync
uv run python scripts_create_admin.py admin@example.com 'StrongPass123'
uv run fastapi dev app/main.py  # docs at http://127.0.0.1:8000/docs
```

## Structure
- `app/core` config, database, security (JWT), dependencies (auth/roles)
- `app/models` SQLAlchemy tables
- `app/schemas` Pydantic request/response models
- `app/services` business logic (auth, reserve/pay/cancel with row locking)
- `app/api/routes` thin HTTP layer

## Roadmap (P1/P2)
QR codes + email (BackgroundTasks) · rate limiting (slowapi) · refunds · analytics · audit logs · Alembic
