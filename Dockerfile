FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir '.[auth]' && useradd -m -u 10001 appuser
COPY config ./config
RUN mkdir -p /app/data && chown -R appuser:appuser /app
USER appuser
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health')"
CMD ["uvicorn","universal_api_orchestrator.main:app","--host","0.0.0.0","--port","8080","--workers","1","--no-access-log"]
