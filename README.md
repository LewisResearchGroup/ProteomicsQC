# Django based proteomics pipeline server using MaxQuant and RawTools

A server that runs proteomics analysis jobs. 
The server be easily spun up with docker-compose.

This repository contains git submodules and should be cloned with:
    git clone --recursive git@github.com:soerendip/django3-omics-pipelines.git

    ./scripts/generate_config.sh  # generates a .env file for configuration

    make init  # to start the server the first time

    make run  # starts the production server on port 8000


![](./docs/img/workflow.png 'Pipeline Workflow')


[Documentation](https://soerendip.github.io/django3-omics-pipelines/)