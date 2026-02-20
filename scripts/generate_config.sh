#!/bin/bash

echo '# OMICS PIPELINES CONFIG' > .env

echo """
## HOMPAGE SETTINGS
HOME_TITLE='Proteomics Pipelines'
HOSTNAME=localhost
ALLOWED_HOSTS=localhost
CSRF_TRUSTED_ORIGINS=http://localhost
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
RESOURCE_RETRY_SECONDS=60
MIN_FREE_MEM_GB_MAXQUANT=8
MAX_LOAD_PER_CPU_MAXQUANT=0.85
MIN_FREE_MEM_GB_RAWTOOLS=2
MAX_LOAD_PER_CPU_RAWTOOLS=0.95
""" >> .env

echo """##USERID
UID=$(id -u):$(id -g)
""">> .env

echo "## SECURITY KEYS" >> .env
echo "SECRET_KEY=$( openssl rand -hex 32 )" >> .env

# this prevents permission issues
mkdir -p data/{compute,datalake,db,media,static}
chown -R "$USER":"$USER" data
