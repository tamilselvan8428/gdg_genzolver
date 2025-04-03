# Use Python 3.10 for better compatibility
FROM python:3.10

# Set working directory
WORKDIR /app

# Copy files into container
COPY . /app

# Install system dependencies for Selenium and Chrome
RUN apt-get update && apt-get install -y \
    wget unzip curl chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8080 for Cloud Run
EXPOSE 8080

# Run the Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
