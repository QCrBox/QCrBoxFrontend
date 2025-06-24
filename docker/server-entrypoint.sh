#!/bin/sh

echo $(ls)
cd /app/qcrbox_frontend

until python manage.py migrate
do
    echo "Migrating db..."
    sleep 2
done

python manage.py collectstatic --noinput
python manage.py initialise_admin

# for debug
# python manage.py runserver 0.0.0.0:8888
uwsgi --ini uwsgi.ini
