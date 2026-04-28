FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY config ./config
COPY templates ./templates
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import financial_reports" || exit 1
ENTRYPOINT ["/entrypoint.sh"]
