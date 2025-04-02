# Use the official Python image
FROM python:3.9

# Set the working directory
WORKDIR /app

# Copy files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Cloud Run expects
EXPOSE 8080

# Start the Streamlit app
CMD streamlit run app.py --server.port 8080 --server.address 0.0.0.0
