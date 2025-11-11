# Базовый образ Python
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY pyproject.toml poetry.lock ./

# Устанавливаем Poetry и зависимости
RUN pip install --upgrade pip \
    && pip install poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-root

# Копируем весь проект в контейнер
COPY . /app

RUN chmod +x prestart.sh

ENTRYPOINT [ "./prestart.sh" ]

ENV PYTHONPATH=/app/src

# Запуск приложения через Uvicorn с правильным PYTHONPATH
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
