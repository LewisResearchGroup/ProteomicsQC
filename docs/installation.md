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
HOSTNAME=example.com

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
CONCURRENCY=8

## SECURITY KEYS
SECRET_KEY=...
OIDC_RSA_PRIVATE_KEY=...

```

## 4) Initiate database

    make init  # to start the server the first time

## 5) Create an admin account

    make createsuperuser

And follow the instructions to provide an email address and 
password.

## 6) Run the server

    make run  # starts the production server on port 8000

You can now navigate to [localhost:8000/admin](localhost:8000/admin) and login to the
admin account with the credentials you provided in step 5.

> In order to run the server on a specific domain you have to register the domain
> and point it to the public IP address of your server. Furthermore, you have to 
> setup a remote proxy to redirect HTTP and HTTPS requests to port 8000. 
> For security reasons you should always use HTTPS. The server was tested using
> a remote proxy configured with NGINX and for encryption we used letsencrypt and 
> certbot.