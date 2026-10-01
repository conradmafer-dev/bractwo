FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt

# Explicit copies prevent saves, secrets and test accounts entering the image.
COPY server/ ./server/
COPY web/ ./web/
COPY tools/precompress_web.py ./tools/precompress_web.py
RUN python tools/precompress_web.py web
COPY run.py LICENSE-SRD.txt ./

EXPOSE 8080
STOPSIGNAL SIGTERM
CMD ["python", "run.py"]
