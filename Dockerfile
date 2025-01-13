# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /src

# Copy the current directory contents into the container at /app
COPY /src .
COPY requirements.txt .

# Install the required Python packages
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8501

# Run main.py when the container launches
ENTRYPOINT ["streamlit", "run", "main.py", "--server.port=8501"]