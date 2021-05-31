# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory to /webapp
WORKDIR /webapp

# Copy the current directory contents into the container at /webapp
COPY . /webapp

# Install any needed packages specified in requirements.txt
RUN apt-get update -y && apt-get install -y gcc
RUN pip3 install --trusted-host pypi.python.org -r requirements.txt
RUN apt-get remove -y --purge gcc
RUN apt autoremove -y
RUN rm -rf /var/lib/apt/lists/*

ENV FLASK_APP main.py
ENV FLASK_RUN_HOST 0.0.0.0
ENV FLASK_ENV production
ENV FLASK_DEBUG 0

# Make port 80 available to the world outside this container
#EXPOSE 5000

# Run main.py when the container launches
CMD ["flask", "run"]