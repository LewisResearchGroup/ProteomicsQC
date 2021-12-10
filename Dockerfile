FROM continuumio/miniconda3

RUN cat /etc/os-release

ENV PYTHONUNBUFFERED=1

RUN mkdir /data /compute /static /appmedia

RUN apt update && apt install -y build-essential time

RUN python --version

RUN conda install -c conda-forge -c bioconda pip rawtools maxquant=1.6.10.43 mono=5

COPY requirements.txt requirements_app.txt

RUN pip install -r requirements_app.txt

COPY ./lib/lrg_omics/requirements.txt requirements_lrg_omics.txt

RUN pip install -r requirements_lrg_omics.txt

RUN conda update --all

COPY ./lib/lrg_omics /lrg-omics

RUN cd /lrg-omics && pip install -e .

COPY ./app /app

WORKDIR /app/
