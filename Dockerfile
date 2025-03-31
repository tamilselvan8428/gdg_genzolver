# Use official Python image
FROM python:3.9

# Set the working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port 8080 for Cloud Run
EXPOSE 8080

# Run the app
CMD ["python", "app.py"]
