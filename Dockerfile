FROM python:3.13.9-alpine3.22

WORKDIR /app

RUN apk add --update \
  curl \
  && rm -rf /var/cache/apk/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python && \
  cd /usr/local/bin && \
  ln -s /opt/poetry/bin/poetry && \
  poetry config virtualenvs.create false

COPY ./pyproject.toml ./poetry.lock* /app/

RUN poetry lock && poetry install --no-root

COPY ./incidentbot /app/incidentbot
COPY ./main.py /app
COPY ./alembic.ini /app
COPY ./alembic/ /app/alembic/

CMD ["python3", "main.py"]
