The docker-compose setup spins up two docker containers. One for the 
web-page and one for the the postgres database.

`make build` to build the containers

`make migrations` to create database migrations

`make migrate` to migrate the database

`make createsuperuser` to create credentials for a superuser

`make run` to run the website and postgres database. 

`make init` initiate the database