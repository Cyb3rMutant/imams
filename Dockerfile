# Base image
FROM python:3.14.4

# Set working directory
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements ./
RUN pip install -r requirements

# Copy all source code over
COPY . .

# Expose port 8000
EXPOSE 8000
