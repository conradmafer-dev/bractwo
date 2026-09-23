FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    GAME_HOST=0.0.0.0

WORKDIR /app

COPY server/requirements.txt /app/server/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /app/server/requirements.txt

COPY . /app

# Railway injects PORT at runtime. server.py reads it directly.
CMD ["python", "server/server.py"]
