# Dockerfile
FROM python:3.10

# set working directory
WORKDIR /dompet

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install system dependencies
RUN apt-get update -y
RUN apt-get install -y netcat-traditional

# install dependencies
COPY requirements.txt requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# create static folder
RUN mkdir /dompet/static

# copy all files
COPY . .

# copy entrypoint.sh
COPY ./entrypoint.sh .
RUN chmod +x /dompet/entrypoint.sh

# run entrypoint.sh
ENTRYPOINT ["/dompet/entrypoint.sh"]