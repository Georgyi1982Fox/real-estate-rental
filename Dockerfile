# Образ бэкенда Bina.ai: API, бот, парсер и миграции (TASK-039).
# Какую программу запустить, задаёт docker-compose.yml (command).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Сначала только зависимости: при изменении кода этот слой берётся из кэша
COPY pyproject.toml README.md ./
RUN mkdir -p src/bina && touch src/bina/__init__.py \
    && pip install . \
    && pip uninstall -y bina \
    && rm -rf src

# Код и миграции (alembic.ini ссылается на src/bina/infrastructure/db/alembic)
COPY src ./src
COPY alembic.ini ./
RUN pip install --no-deps .

# Не от root
RUN useradd --create-home --uid 1000 bina
USER bina

EXPOSE 8000
CMD ["bina-api", "--host", "0.0.0.0", "--port", "8000"]
