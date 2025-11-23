FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY node.py .
COPY picture_pb2.py picture_pb2_grpc.py ./
RUN mkdir -p /data/pictures
CMD ["python", "node.py"]