# Use a Python base image
FROM python:3.12-slim

WORKDIR /home
COPY dyn_generator_w_fastAPI.py dyn_generator.py
COPY start_container.sh .
COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && \
    apt-get install -y sysstat && \
    chmod +x start_container.sh

# Create a directory for the MongoDB data
RUN mkdir -p /data && \
    touch /data/db1.db && \
    touch /data/db2.db

EXPOSE 23456
# Start MongoDB and run the Python client script
CMD /home/start_container.sh
