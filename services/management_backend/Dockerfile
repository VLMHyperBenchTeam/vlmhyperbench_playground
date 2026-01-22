FROM python:3.13-slim

# Устанавливаем системные зависимости, необходимые для инсталлятора uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем uv через официальный скрипт
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Добавляем путь к бинарникам uv в PATH
ENV PATH="/root/.local/bin/:${PATH}"

WORKDIR /app

# Копируем конфиги и локальные зависимости
COPY services/management_backend/pyproject.toml ./
COPY packages/task-registry /workspace/packages/task-registry

# Устанавливаем зависимости через uv
# Используем --no-cache и явно указываем установку зависимостей из pyproject.toml
RUN uv pip install --system --no-cache -e /workspace/packages/task-registry
RUN uv pip install --system --no-cache fastapi uvicorn pydantic sqlmodel redis httpx

# Копируем исходный код сервиса
COPY services/management_backend/src ./src

EXPOSE 8000

# Убеждаемся, что PYTHONPATH включает src
ENV PYTHONPATH=/app/src

CMD ["python", "-m", "management_backend.main"]