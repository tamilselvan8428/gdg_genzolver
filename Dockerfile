# Use official Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Selenium
RUN apt-get update && apt-get install -y \
    curl unzip xvfb libxi6 libgconf-2-4 \
    chromium chromium-driver && \
    apt-get clean

# Install required Python packages
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Set environment variables for headless Chrome
ENV DISPLAY=:99

# Expose the Streamlit default port
EXPOSE 8501

# Start Xvfb for virtual display and run the app
CMD ["sh", "-c", "Xvfb :99 -screen 0 1024x768x16 & streamlit run app.py --server.port=8501 --server.enableCORS=false --server.enableXsrfProtection=false"]
