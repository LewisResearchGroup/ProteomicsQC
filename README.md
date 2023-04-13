![](docs/img/ProteomicsQC.jpg)

# **ProteomicsQC**: Quality Control Server for large-cohort quantitative proteomics using tandem-mass-tags (e.g. TMT11)

A quality control (QC) pipeline server for quantitative proteomics, automated processing, and interactive visualisations of QC results.
The server allows to setup multiple proteomics pipelines grouped by projects. 
The user can drag and drop new RAW mass spectrometry files which are processed automatically. 
Results are visualized in an interactive dashboard and accessible via a RESTful API for third party applications and extensions.
The server can be started with a single command using `docker-compose`.
Underlying software is _MaxQuant_ and _RawTools_ for proteomics, _Django_ for the web-server and API and _Plotly/Dash_ for the interactive dashboard.

More information can be found in the [Documentation](https://LewisResearchGroup.github.io/ProteomicsQC/).

## Installation

This repository contains git submodules and should be cloned with:

    git clone --recursive git@github.com:LewisResearchGroup/ProteomicsQC.git

    ./scripts/generate_config.sh  # generates a .env file for configuration

    make init  # to start the server the first time

    make devel  # starts a development server on port 8000
    
    make serve  # starts the production server on port 8000


## Limitations
The pipeline is restricted to single file setup which might conflict with the setup of some laboratories that split sample results into multiple files. The pipeline processes each file separately and independently.

## Overview

The server manages proteomics pipelines belonging to multiple projects. The server is mostly implemented in Python and is composed of several components such as a PostgreSQL database, a queuing system (Celery, Redis), a dashboard (Plotly-Dash) and an API (Django REST-Framwork).

<img src="./docs/img/workflow.png" width="100%">

## Features

1.  Different project spaces    
2.  Setup of different pipelines (using MaxQuant and RawTools)
3.  Upload .RAW files and automatic submission to a job queueing system
4.  Data management of input and output files
5.  User rights management
6.  Data API for programmatic file submission and download of results
7.  Dashboard for quality control (QC)
8.  Anomaly detection with Isolation Forest and explainable AI using SHAP

## The GUI

### Pipelines overview
The server has a simple static http frontend and admin view, generated with Django; and a dynamic and interactive dashboard implemented with Plotly-Dash. The Project detail-view, for example, shows and overview over all pipelines associated with the current project and the number of submitted files.

<img src="./docs/img/Pipelines.png" width="100%">

### Admin view

Django is a popular web framework for building web applications in Python. The Django admin view is a built-in feature of Django that provides an easy-to-use interface for managing the application's data models. The admin view is automatically generated based on the models defined in the application's code, and allows administrators to perform CRUD (Create, Read, Update, and Delete) operations on the application's data. This way new projects, and pipelines can be setup. It also provides an overview over all results and raw files stored on the server and can be used for troubleshooting, if some runs are unsuccessful.

![](./docs/img/example-admin-view.png 'Overview over all jobs on the server.')

## Dashboard

When the user drops a file to the web-upload page of a particular pipeline, it is automatically processed and the results are sent to the dashboard.
Here, all quality control metrics can be visualized simultaneously in customized order, and the relationships between QC metrics can be plotted.
Timelines of up to 60 quality control metrics can be viewed simultanously in one place. 

-   `accepted` samples for downstream processing have a dark hue
-   `rejected` samples have a brighter hue 
-   `normal` samples are colored blue
-   `flagged` samples, potential outliers, are colored red 

![](./docs/img/QC-barplot-small.jpg 'Many customiable Quality Control metrics in one place.')

### Explainable AI to gain insights into anomaly detection

In order to assist users in identifying abnormal trends within the extensive feature space, both outlier detection techniques and explainable AI methods are employed. Specifically, algorithms such as Isolation Forest or other comparable outlier detection approaches can be utilized to spot unusual patterns. These algorithms are then analyzed using the SHapley Additive exPlanations (SHAP) algorithm, which is a powerful tool for interpreting the output of machine learning models. By applying the SHAP algorithm, a plot can be generated that emphasizes the particular features that deviate significantly from normal statistical behavior, making it easier for users to understand the underlying causes of these anomalies.

![](./docs/img/XAI-small.jpg 'Many customiable Quality Control metrics in one place.')

