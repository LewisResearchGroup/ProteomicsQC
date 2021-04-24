# Django based proteomics pipeline server using MaxQuant and RawTools

A server that automates proteomics processing jobs.

This repository contains git submodules and should be cloned with:

    git clone --recursive git@github.com:soerendip/django3-omics-pipelines.git

    ./scripts/generate_config.sh  # generates a .env file for configuration

    make init  # to start the server the first time

    make run  # starts the production server on port 8000

More information can be found in the [Documentation](https://soerendip.github.io/django3-omics-pipelines/).

# Overview

The server manages proteomics pipelines belonging to multiple projects. 

![](./docs/img/workflow.png 'The workflow managed by the proteomics pipeline server.')

The server manages:

    1) Different project spaces    
    2) Setup of different pipelines (using MaxQuant and RawTools)
    3) Upload and processing .RAW files with a job queueing system
    4) Data management of input and output files
    5) User rights
    6) Data API for upload and download of results
    7) Dashboard for Quality Control

## Technology stack

The server uses `docker-compose` to spin off multiple containers and is ready to be scaled up.

![](./docs/img/workflow.png 'The technology stack used by the proteomics pipeline server.')

