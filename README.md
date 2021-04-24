# Django based proteomics processing framework using MaxQuant and RawTools

A server that automates proteomics processing jobs.

This repository contains git submodules and should be cloned with:

    git clone --recursive git@github.com:soerendip/django3-omics-pipelines.git

    ./scripts/generate_config.sh  # generates a .env file for configuration

    make init  # to start the server the first time

    make run  # starts the production server on port 8000

More information can be found in the [Documentation](https://soerendip.github.io/django3-omics-pipelines/).

# Limitations
The pipeline is restricted to single file setup which might conflict with the setup of many laboratories which use workflows where individual runs are split into multiple files and all setups where multiple `.RAW` files have to be analyzed in tandem by MaxQuant. The pipeline processes each file separately and independently to ensure data reproducibility. This setup works very well for comparatively small  microbial samples (with file sizes of around 1-2 GB), but will be incompatible with mammalian samples, where output files have to be split into chunks in order to keep the file size reasonably small. This kind of setup is currently out of scope for the quality control pipeline. 

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

The admin view provides and overview over all proteomics runs with list and detail views.

![](./docs/img/example-admin-view.png 'Overview over all jobs on the server.')


## Technology stack

The server uses `docker-compose` to spin off multiple containers and is ready to be scaled up.
The web server and the celery workers use a shared file system with a defined folder structure as
the datalake, where all input and output files are collected. In addition to the standard output files a
clean version of the data is stored in parquet format for fast read and parallel processing of the 
generated results.

![](./docs/img/technology-stack.png 'The technology stack used by the proteomics pipeline server.')

A dashboard based on Plotly/Dash is used to present quality control metrics as well as insights into
protein identification and quantification.


## Dashboard features

### Many customiable Quality Control metrics in one place
![](./docs/img/example-qc-barplot.png 'Many customiable Quality Control metrics in one place.')

### Scatterplot tool to explore relationships between variables
![](./docs/img/example-qc-scatterplot.png 'Scatterplot tool to explore relationships between variables.')

### Visualization of normalized reporter intensity (TMT11)
![](./docs/img/example-qc-normalied-tmt-intensity.png 'Visualization of normalized reporter intensity (TMT11).')
