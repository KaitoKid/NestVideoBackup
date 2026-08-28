# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy just the requirements file to leverage Docker cache
COPY requirements.txt /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --no-compile -r requirements.txt

# Copy the rest of the application files and normalize permissions because
# Unraid's flash-backed project directory presents source files as root-only.
COPY --chown=99:100 . /app
RUN chmod -R a+rX /app

# Run main.py when the container launches
CMD ["python", "main.py"]
