[![Codacy Security Scan](https://github.com/sorenwacker/ProteomicsQC/actions/workflows/codacy-analysis.yml/badge.svg)](https://github.com/sorenwacker/ProteomicsQC/actions/workflows/codacy-analysis.yml)

![](docs/img/ProteomicsQC.png)

# **ProteomicsQC**: Quality Control Server for Large-Scale Quantitative Proteomics with http-based API

A quality control (QC) pipeline server for quantitative proteomics, automated processing, and interactive visualisations of QC results.
The server allows to setup multiple proteomics pipelines grouped by projects. 
The user can drag and drop new RAW mass spectrometry files which are processed automatically. 
Results are visualized in an interactive dashboard and accessible via a RESTful API for third party applications and extensions.
The server can be started with a single command using `docker-compose`.
Underlying software is _MaxQuant_ and _RawTools_ for proteomics, _Django_ for the web-server and API and _Plotly/Dash_ for the interactive dashboard.

More information can be found in the [Documentation](https://sorenwacker.github.io/ProteomicsQC/).


## Installation

This repository contains git submodules and should be cloned with:

    git clone --recursive git@github.com:sorenwacker/ProteomicsQC.git

    ./scripts/generate_config.sh  # generates a .env file for configuration

    make init  # to start the server the first time

    make devel  # starts a development server on port 8000
    
    make serve  # starts the production server on port 8000


## Limitations
The pipeline is restricted to single file setup which might conflict with the setup of some laboratories that store single sample results in multiple files. The pipeline processes each file separately and independently.


## Features

The server manages proteomics pipelines belonging to multiple projects. The server is mostly implemented in Python and is composed of several components such as a PostgreSQL database, a queuing system (Celery, Redis), a dashboard (Plotly-Dash) and an API (Django REST-Framwork).

![](./docs/img/workflow.png 'The workflow managed by the proteomics pipeline server.')

Feature list:

1. Different project spaces    
2. Setup of different pipelines (using MaxQuant and RawTools)
3. Upload and processing .RAW files with a job queueing system
4. Data management of input and output files
5. User rights management
6. Data API for programmatic file submission and download of results
7. Dashboard for Quality Control
8. Anomaly detection with Isolation Forest and explainable AI using SHAP


## The GUI
The server has a simple static http frontend and admin view, generated with Django; and a dynamic and interactive dashboard implemented with Plotly-Dash.

![](./docs/img/example-admin-view.png 'Overview over all jobs on the server.')
> The admin view provides and overview over all proteomics runs with list and detail views.


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
