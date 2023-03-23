FROM continuumio/miniconda3

RUN cat /etc/os-release

ENV PYTHONUNBUFFERED=1

RUN mkdir /data /compute /static /appmedia

RUN apt update && apt install -y build-essential time

RUN python --version

RUN conda install -c conda-forge -c bioconda pip rawtools maxquant=2 mono=5 mamba

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY ./lib/lrg-omics /lrg-omics

RUN cd /lrg-omics && pip install -e .

COPY new_req.txt new_req.txt

RUN pip install -r new_req.txt

COPY ./app /app

WORKDIR /app/
