# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for some Python packages if necessary
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     # other system deps
#     && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY ./app /app/app

# Expose the port the app runs on
EXPOSE 8003

# Define environment variables (can be overridden by Docker Compose)
ENV PYTHONUNBUFFERED=1
ENV APP_MODULE="app.main:app"
ENV HOST="0.0.0.0"
ENV PORT="8003"
# Add other ENV variables if needed, e.g., for SMTP, default emails

# Command to run the application using Uvicorn
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
# Using the environment variables for flexibility:
CMD ["uvicorn", "$APP_MODULE", "--host", "$HOST", "--port", "$PORT"]
