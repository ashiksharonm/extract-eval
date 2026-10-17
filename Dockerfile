# syntax=docker/dockerfile:1
FROM python:3.11-slim AS build
WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir build && python -m build --wheel --outdir /dist

FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 GRADIO_ANALYTICS_ENABLED=False
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=build /dist/*.whl /tmp/
RUN pip install /tmp/*.whl "gradio>=4.44,<6" && rm /tmp/*.whl
COPY --chown=app:app space/app.py ./app.py
COPY --chown=app:app examples ./examples
USER app
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:7860/').status==200 else 1)"
CMD ["python", "app.py"]
