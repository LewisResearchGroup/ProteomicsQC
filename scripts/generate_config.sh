#!/bin/bash

echo '# OMICS PIPELINES CONFIG' > .env

echo """
## HOMPAGE SETTINGS
HOME_TITLE='Proteomics Pipelines'
HOSTNAME=localhost
ALLOWED_HOSTS=localhost
""" >> .env

echo """## STORAGE
DATALAKE=./data/datalake
COMPUTE=./data/compute
MEDIA=./data/media
STATIC=./data/static
DB=./data/db
""" >> .env

echo """## EMAIL SETTINGS
EMAIL_HOST=smtp.gmail.com
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_PORT=587
EMAIL_HOST_USER=''
EMAIL_HOST_PASSWORD=''
DEFAULT_FROM_EMAIL=''
""" >> .env

echo """## CELERY
CONCURRENCY=8
""" >> .env

echo """##USERID
UID=$(id -u):$(id -g)
""">> .env

echo "## SECURITY KEYS" >> .env
echo "SECRET_KEY=`openssl rand -hex 32`" >> .env
