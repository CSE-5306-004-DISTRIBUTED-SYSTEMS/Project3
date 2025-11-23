FROM python:3.11-slim
ARG SERVICE
WORKDIR /app
COPY . /app/python_architecture
WORKDIR /app/python_architecture
ENV PYTHONPATH=/app
ENV SERVICE=${SERVICE}
CMD ["python", "-m", "python_architecture.service_runner"]
