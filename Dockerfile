# Production image: one small container serves the API *and* the built app.
# Build:  docker build -t chrystalclear .
# Run:    docker run -p 8000:8000 --env-file .env chrystalclear

FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    APP_ENV=production FRONTEND_DIST_DIR=/app/static STORAGE_BACKEND=database
WORKDIR /app
COPY backend/pyproject.toml ./
RUN mkdir app && touch app/__init__.py && pip install . && rm -rf app
COPY backend/ ./
# Team-written repair content (proprietary, see content/LICENSE), loaded by the seed.
COPY content/ ./content/
COPY --from=web /web/dist ./static
RUN useradd --create-home appuser
USER appuser
EXPOSE 8000
# PORT is set by most hosts (Render, Railway, Fly, Cloud Run); 8000 otherwise.
# The host's proxy passes the real visitor address, which rate limiting needs.
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
