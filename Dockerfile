# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask script
COPY . /app

# Set environment variable to run Flask
ENV FLASK_APP=backend.py

# Expose the port Flask runs on
EXPOSE 5000

# Run the Flask server
CMD ["python3", "backend.py"]