FROM node:26.11-alpine AS web-build
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@11.19.0 --activate
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY index.html tsconfig*.json vite.config.ts ./
COPY public ./public
COPY src ./src
RUN pnpm build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    EXPERIMENTLENS_HOST=0.0.0.0 \
    EXPERIMENTLENS_PORT=5050
WORKDIR /app
RUN groupadd --system experimentlens && useradd --system --gid experimentlens experimentlens
COPY pyproject.toml README.md alembic.ini ./
COPY migrations ./migrations
COPY py-src ./py-src
COPY evals ./evals
COPY --from=web-build /app/dist ./dist
RUN pip install --no-cache-dir . && mkdir -p /app/.experimentlens && chown -R experimentlens:experimentlens /app
USER experimentlens
EXPOSE 5050
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5050/api/v2/health/ready', timeout=2)"
CMD ["sh", "-c", "alembic upgrade head && experimentlens-api"]
