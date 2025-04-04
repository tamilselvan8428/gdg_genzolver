# Use slim Python image to reduce size
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
RUN apt-get update && apt-get install -y \
    chromium chromium-driver


# Set environment variables for Chromium
ENV CHROME_BIN=/usr/bin/chromium
ENV PATH=$CHROME_BIN:$PATH
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy everything
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Streamlit requires this to work correctly in Cloud Run
ENV PORT 8080

# Start Streamlit on port 8080
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
