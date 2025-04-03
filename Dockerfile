# Use official Python image
FROM python:3.10

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget unzip curl \
    chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for Selenium
ENV PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/usr/lib/chromium"

# Set working directory
WORKDIR /app

# Copy app files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8080

# Run the Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
