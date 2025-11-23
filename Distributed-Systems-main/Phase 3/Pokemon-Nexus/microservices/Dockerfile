# Use the official Python image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install dependencies
COPY ./web/requirements.txt  .
RUN pip install --no-cache-dir -r ./requirements.txt

# Copy the application code to the container
# This copies all the Python services and the client files
COPY ./web ./web 

# Expose ports used by services (5000 for HTTP, 5001 for SocketIO)
EXPOSE 5000
EXPOSE 5001

# No default CMD, as each service defines its own execution command
