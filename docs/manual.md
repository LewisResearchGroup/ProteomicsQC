# User manual

## Start the pipeline server and the celery workers.

To run the server both the celery workers and the django server have to be started. This can be done running the scripts:

    scripts/omics_celery_worker.sh    

    scripts/omics_server.sh        

    >Starting omics server
    >LOAD MAXQUANT DASHBOARD
    >Dashboard API URL:http://localhost:8000
    >URL: http://localhost:8000/api/projects
    >LOAD PRIMARY DASHBOARD
    >Serving on http://0.0.0.0:8123


After installation the webinterface can be reached with the browser. By default the server runs on address [http://localhost:8123](http://localhost:8123).
This can be changed in the configuration file (`OMICS.conf`).


## Login with an admin account

![](img/login.png)


![](img/click-on-admin.png)


## Setup MaxQuant

To setup MaxQuant you can upload a zipped MaxQuant version. 
Version 1.6.14 works with [Mono](https://www.mono-project.com/docs/about-mono/) and is the recommended version to use with the Proteomics Pipelines server.
Please contact the MaxQuant [mailing list](https://groups.google.com/u/1/g/maxquant-list/c/X94RkHSoEYo/m/LuYDKHskDwAJ) for information on how to obtain older versions. 

Once you downloaded the zip-file you can upload it to the Pipeline server. Go to 'admin/pipelines/maxquantbin/add' and upload the zip file from 
[Admin / Max quant bins / ADD MAX QUANT BIN](http://localhost:8000/admin/pipelines/maxquantbin/add/). If successful the executable will be selectable under [Admin / Max quant setups / ADD MAX QUANT SETUP/](http://localhost:8000/admin/pipelines/maxquantsetup/add/).

![](img/select-maxquant-bin.png)

If this is done you can create your first pipeline. 

## Create first pipeline

### 1. Create a new project
At least one project has to be set up. Navigate to [Admin / Projects / ADD PROJECT](http://localhost:8000/admin/pipelines/project/) and provide 
a name and a description. 


### 2. Upload Fasta File

A fasta file with protein sequences has to be uploaded. 

### 3. Upload mqpar.xml

A `mqpar.xml` file has to be provided for each pipeline. It has to be created using the MaxQuant GUI. Only a single `.RAW` file should be included.

### 4. Create MaxQuant Setup

The MaxQuant Setup defines a pipeline. It is a combination of a MaxQuant binary, a MaxQuant parameter file (mqpar.xml) and a Fasta file. 
Once created you will be able to submit `.RAW` files to this pipeline. 

### 5. Setup RawFile type for RawTools















