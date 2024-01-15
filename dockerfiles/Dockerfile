FROM continuumio/miniconda3:latest

RUN cat /etc/os-release

ENV PYTHONUNBUFFERED=1

RUN mkdir /data /compute /static /appmedia /datalake

RUN apt-get update && \
    apt-get install -y build-essential time \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN python --version

#RUN conda install -c conda-forge -c bioconda pip rawtools maxquant=1.6.10.43 mono=5 mamba
RUN conda install -c conda-forge -c bioconda pip rawtools maxquant=2 mono=5

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY ./lib/lrg-omics /lrg-omics

RUN cd /lrg-omics && pip install -e .

# Used for testing
# COPY new_req.txt new_req.txt
# RUN pip install -r new_req.txt

RUN chown 1000:1000 /data /compute /static /appmedia /datalake

COPY ./app /app

WORKDIR /app/
