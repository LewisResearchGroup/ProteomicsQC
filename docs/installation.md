# Installation
## 1) Docker-compose

The server can be started with `docker-compose`. Therefore,
docker and docker-compose have to be installed on the host.
The server can also be used without docker-compose, 
if the postgres and redis servers are running already. 

For official Docker installation instructions please visit:

https://docs.docker.com/engine/install/ubuntu/


## 2) Download the repository

    git clone --recursive git@github.com:LSARP/ProteomicsQC.git ProteomicsQC
    cd ProteomicsQC

## 3) Create configuration file

    ./scripts/generate_config.sh  # generates a .env file for configuration

### Edit the .env file

```
# OMICS PIPELINES CONFIG

## HOMPAGE SETTINGS
HOME_TITLE=Your Hompage Title
HOSTNAME=localhost:8080
ALLOWED_HOSTS=localhost
CSRF_TRUSTED_ORIGINS=http://localhost

## STORAGE
DB=./data/db/
DATALAKE=./data/datalake
COMPUTE=./data/compute
MEDIA=./data/media
STATIC=./data/static

## EMAIL SETTINGS
EMAIL_HOST=smtp.gmail.com
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_PORT=587
EMAIL_HOST_USER=example@example.com
EMAIL_HOST_PASSWORD=a-strong-password
DEFAULT_FROM_EMAIL=noreply@example.com

## CELERY
CONCURRENCY=8  # Change this to control how many CPU's can be used for jobs
RESOURCE_RETRY_SECONDS=60
MIN_FREE_MEM_GB_MAXQUANT=8
MAX_LOAD_PER_CPU_MAXQUANT=0.85
MIN_FREE_MEM_GB_RAWTOOLS=2
MAX_LOAD_PER_CPU_RAWTOOLS=0.90

## RESULT STATUS (web UI responsiveness vs strictness)
RESULT_STATUS_INSPECT_TIMEOUT_SECONDS=10.0
RESULT_STATUS_PENDING_STALLED_WARNING_SECONDS=7200
RESULT_STATUS_DONE_MTIME_SKEW_SECONDS=300
RESULT_STATUS_MAXQUANT_STALE_SECONDS=21600
RESULT_STATUS_RAWTOOLS_STALE_SECONDS=3600
RESULT_STATUS_ACTIVITY_FALLBACK_SECONDS=300
RESULT_STATUS_INSPECT_MAX_VISIBLE_RUNS=25
RESULT_STATUS_INSPECT_MAX_ACTIVE_RUNS=12

## SECURITY KEYS
SECRET_KEY=...

```

The queue is resource-aware. Before each task starts, the worker checks current
machine load and available memory. If thresholds are exceeded, the task is deferred
and retried after `RESOURCE_RETRY_SECONDS`.

For large pipelines, tune result-status responsiveness via:
- `RESULT_STATUS_INSPECT_MAX_VISIBLE_RUNS`
- `RESULT_STATUS_INSPECT_MAX_ACTIVE_RUNS`

Lower values prioritize web responsiveness by avoiding expensive queue
inspection on large run lists.

## 4) Initiate database

    make init  # to start the server the first time

## 5) Create an admin account

    make createsuperuser

And follow the instructions to provide an email address and 
password.

## 7) Run a development server (Optional)

    make devel  # starts the production server on port 8080

The development server will run on [localhost:8000](localhost:8000).

## 8) Run the server in production

    make collectstatic  # The static url has to be setup with a remote proxy.
    make serve  # starts the production server on port 8000

You can now navigate to [http://localhost:8080/admin](http://localhost:8080/admin) and login to the
admin account with the credentials you provided in step 5. To make this work you have to 
configure a remote server that exposes forwards traffic to ports 80 (http) or 443 (https)
to port 8080 and back. We recommend using NGINX for this purpose.
