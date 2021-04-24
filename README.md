# Django based proteomics pipeline server using MaxQuant and RawTools

A server that automates proteomics processing jobs.

This repository contains git submodules and should be cloned with:

    git clone --recursive git@github.com:soerendip/django3-omics-pipelines.git

    ./scripts/generate_config.sh  # generates a .env file for configuration

    make init  # to start the server the first time

    make run  # starts the production server on port 8000

More information can be found in the [Documentation](https://soerendip.github.io/django3-omics-pipelines/).

# Overview

![](./docs/img/workflow.png 'Pipeline Workflow')

The server manages proteomics pipelines belonging to multiple projects. The server manages:

    1) Input files
    2) Setup of different pipeline
    3) Upload and processing .RAW files in a job queue
    4) Data management of input and output files
    5) User rights
    6) Data API for upload and download of results
    7) Dashboard for Quality Control

The server uses `docker-compose` to spin off multiple containers and ready to be scaled up.
