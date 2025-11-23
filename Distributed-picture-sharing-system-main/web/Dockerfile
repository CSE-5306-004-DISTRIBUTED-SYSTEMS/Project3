FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY templates/ templates/
# Copy gRPC generated files
COPY picture_pb2.py picture_pb2_grpc.py ./
CMD ["python", "app.py"]