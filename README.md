# A basic django website with redis and postgres using docker-compose

The docker-compose setup spins up two docker containers. One for the 
web-page and one for the the postgres database.

`make build` to build the containers

`make migrations` to create database migrations

`make migrate` to migrate the database

`make createsuperuser` to create credentials for a superuser

`make run` to run the website and postgres database. 


lrg_run_maxquant.py --fasta /datalake/P/P1/P1MQ5/config/fasta.faa --mqpar /datalake/P/P1/P1MQ5/config/mqpar.xml --raw /datalake/P/P1/P1MQ5/inputs/SA010-R1-blank-200425-R2.raw --run-dir /tmp/run --maxquantcmd 'mono /compute/software/MaxQuant/MaxQuant_1.6.14.zip/MaxQuant_1.6.14/MaxQuant/bin/MaxQuantCmd.exe' --run --rerun