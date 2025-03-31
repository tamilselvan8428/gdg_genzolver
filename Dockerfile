# Use the official Python base image
FROM python:3.10

# Set the working directory
WORKDIR /app

# Copy the app files into the container
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Streamlit runs on
EXPOSE 8501

# Run Streamlit when the container starts
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
