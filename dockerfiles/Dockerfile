FROM continuumio/miniconda3:latest

RUN cat /etc/os-release

ENV PYTHONUNBUFFERED=1

RUN mkdir /data /compute /static /appmedia /datalake

RUN apt-get update && apt install -y build-essential time

RUN python --version

RUN conda install -c conda-forge -c bioconda pip rawtools maxquant=2 mono=5 mamba

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY ./lib/lrg-omics /lrg-omics

RUN cd /lrg-omics && pip install -e .

COPY new_req.txt new_req.txt

RUN pip install -r new_req.txt

RUN chown 1000:1000 /data /compute /static /appmedia /datalake

COPY ./app /app

WORKDIR /app/
