# Backend (FastAPI)

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head        # create/upgrade the database (SQLite by default)
python -m app.seed          # load sample data
uvicorn app.main:app --reload
# API docs: http://localhost:8000/api/v1/docs
pytest                      # run tests
ruff check . && ruff format --check .
```

Layout: `app/core` (security, errors, permissions), `app/modules/<feature>` (one folder
per feature: models, schemas, service, router), `app/seed` (sample data), `alembic`
(database migrations). After changing models: `alembic revision --autogenerate -m "what changed"`.
