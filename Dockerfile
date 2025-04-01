# Use the official Python image
FROM python:3.9

# Set the working directory
WORKDIR /app

# Copy the files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port for Streamlit
EXPOSE 8501

# Start the Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
