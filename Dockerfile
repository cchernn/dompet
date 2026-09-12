# Local deployment only. AWS Lambda deploys via Setup.py::uploadLambda instead
# (see scripts/deploy/lambda.sh) and does not use this image.
FROM python:3.12-slim

WORKDIR /srv/app

COPY requirements-local.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements-local.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
