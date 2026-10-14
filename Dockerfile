FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY fastserver.py ./

FROM base AS test
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY tests/ ./tests/
RUN python -m unittest discover -s tests -v

FROM base AS runtime
ARG APP_VERSION=local
ARG SOURCE_REVISION=uncommitted
ENV APP_VERSION=${APP_VERSION} \
    SOURCE_REVISION=${SOURCE_REVISION}
USER 10001:10001
EXPOSE 8080
CMD ["python", "fastserver.py", "--port", "8080"]
