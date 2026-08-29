FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./
COPY archive_monitor ./archive_monitor
RUN pip install --no-cache-dir .

RUN useradd --system --uid 10001 monitor
USER monitor
ENTRYPOINT ["python", "-m", "archive_monitor.app"]