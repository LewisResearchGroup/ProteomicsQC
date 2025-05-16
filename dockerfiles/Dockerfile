FROM continuumio/miniconda3:latest

# Downgrade conda python to python 3.10
RUN conda install -y python=3.10

RUN cat /etc/os-release

ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y build-essential time \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN python --version

#add uv package really fast for installations
RUN conda install -c conda-forge -c bioconda pip rawtools maxquant=2.0.3.0 mono=5 uv

COPY requirements.txt requirements.txt

# add this to avoid issues with matplotlib installation
ENV MPLCONFIGDIR=/tmp/matplotlib

# add uv to install
RUN uv pip install --system -r requirements.txt

COPY ./lib/lrg-omics /lrg-omics

RUN cd /lrg-omics && pip install -e .

# Used for testing
# COPY new_req.txt new_req.txt
# RUN pip install -r new_req.txt

COPY ./app /app

WORKDIR /app/
