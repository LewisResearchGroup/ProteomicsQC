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

    1. Different project spaces    
    2. Setup of different pipelines (using MaxQuant and RawTools)
    3. Upload and processing .RAW files with a job queueing system
    4. Data management of input and output files
    5. User rights
    6. Data API for upload and download of results
    7. Dashboard for Quality Control

## Technology stack

The server uses `docker-compose` to spin off multiple containers and is ready to be scaled up.
The web server and the celery workers use a shared file system with a defined folder structure as
the datalake, where all input and output files are collected. In addition to the standard output files a
clean version of the data is stored in parquet format for fast read and parallel processing of the 
generated results.

![](./docs/img/technology-stack.png 'The technology stack used by the proteomics pipeline server.')

A dashboard based on Plotly/Dash is used to present quality control metrics as well as insights into
protein identification and quantification.
