FROM python:3.12-slim

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY models/ models/

ENV PYTHONUNBUFFERED=1

# O Cloud Run informa a porta pela variável PORT.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
