# Installation
## 1) Docker-compose

The server can be started with `docker-compose`. Therefore,
docker and docker-compose have to be installed on the host.
The server can also be used without docker-compose, 
if the postgres and redis servers are running already. 

For official Docker installation instructions please visit:

https://docs.docker.com/engine/install/ubuntu/


## 2) Download the repository

    git clone --recursive git@github.com:soerendip/django3-omics-pipelines.git

## 3) Create configuration file

    ./scripts/generate_config.sh  # generates a .env file for configuration

## 4) Initiate database

    make init  # to start the server the first time

## 5) 
    make run  # starts the production server on port 8000
