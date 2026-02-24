# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy just the requirements file to leverage Docker cache
COPY requirements.txt /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN groupadd -g 1000 nestbackup && \
    useradd -u 1000 -g nestbackup -s /bin/false nestbackup

# Copy the rest of the application files
COPY . /app
RUN chown -R nestbackup:nestbackup /app

USER nestbackup

# Run main.py when the container launches
CMD ["python", "main.py"]
