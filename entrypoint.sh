#!/bin/sh

echo 'Waiting for postgres...'

echo $DB_POSTGRESQL_HOST $DB_POSTGRESQL_PORT

while ! nc -z $DB_POSTGRESQL_HOST $DB_POSTGRESQL_PORT; do
    sleep 0.1
done

echo 'PostgreSQL started'

echo "Running migrations..."
python3 manage.py migrate

echo "Collecting static files..."
python3 manage.py collectstatic --no-input

exec "$@"