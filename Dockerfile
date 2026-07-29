FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --system finops \
    && useradd --system --gid finops --create-home finops

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

USER finops
ENTRYPOINT ["platform-cost"]
CMD ["--help"]

