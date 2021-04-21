# Django3 Omics Pipelines

A web-server to setup processing pipelines proteomics .RAW files.

1) Create a project
2) Create a pipeline by providing a fasta file and a MaxQuant parameter template (mqpar.xml)
3) Submit .RAW files to the pipeline
4) Download results
5) Explore data with the integrated dashboard

The server organizes files into projects. Therefore, at least one project hast to be created.
Then a pipeline can be created. Herefore, a MaxQuant parameter file (mqpar.xml) and a fasta file have to 
be provided. 

## MaxQuant Parameter file (`mqpar.xml`)
The `mqpar.xml` has to be created as a blueprint for the pipeline jobs for example using 
the MaxQuant GUI. The pipeline is currently restricted to process a single .RAW per job, 
therefore the `mqpar.xml` file __has to be created with a single .RAW file__. 
The MaxQuant version supported is `MaxQuant 1.6.10` due to limited compatability 
between `.NET` versions used by MaxQuant and current `mono` versions. `mono` is a 
reimplementation for `.NET` that runs on Linux platforms.ll


##