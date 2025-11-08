# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any needed dependencies specified in requirements.txt
RUN apt-get update && apt-get install -y netcat-openbsd && \
    pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the app directory to the working directory
COPY ./app ./app

# Copy the entrypoint script
COPY ./entrypoint.sh .
RUN chmod +x ./entrypoint.sh

# Set the entrypoint script
ENTRYPOINT ["./entrypoint.sh"]

# Expose port 8000 to the outside world
EXPOSE 8000
