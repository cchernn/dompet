# Dockerfile

FROM python:3.10

WORKDIR /dompet

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements.txt requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY .env .

EXPOSE 8000

CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]