# Сборочный слой: компиляторы и dev-заголовки остаются здесь и в финальный
# образ не попадают.
FROM python:3.12-slim AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


FROM python:3.12-slim

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=builder /opt/venv /opt/venv

# Приложение работает от непривилегированного пользователя.
# ВНИМАНИЕ: существующие тома static_volume/media_volume принадлежат root —
# после первого деплоя этого образа нужен одноразовый chown, см. docs/deploy.md.
RUN useradd --system --uid 10001 --create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --chown=app:app . .
RUN mkdir -p /app/staticfiles /app/media && chown -R app:app /app/staticfiles /app/media

USER app

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
