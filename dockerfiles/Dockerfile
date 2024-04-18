FROM ubuntu:23.10

SHELL ["/bin/bash", "-c"]

ENV PYTHONUNBUFFERED=1

RUN mkdir /data /compute /static /appmedia /datalake

# Get OS version info
RUN cat /etc/os-release

RUN apt-get update && apt-get install -y wget

# Download Microsoft signing key and repository
RUN wget https://packages.microsoft.com/config/ubuntu/23.10/packages-microsoft-prod.deb -O packages-microsoft-prod.deb

# Install Microsoft signing key and repository
RUN dpkg -i packages-microsoft-prod.deb

# Clean up
RUN rm packages-microsoft-prod.deb

RUN apt-get update && \
    apt-get install -y build-essential time dotnet-sdk-7.0 aspnetcore-runtime-7.0\
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-Linux-x86_64.sh 

RUN chmod +x Mambaforge-Linux-x86_64.sh && bash Mambaforge-Linux-x86_64.sh -b -p miniforge\
    && rm -f Miniforge3-Linux-x86_64.sh 

# Initialize Mamba
RUN /miniforge/bin/mamba init --quiet

SHELL ["/miniforge/bin/mamba", "run", "-p", "/miniforge", "/bin/bash", "-c"]

RUN mamba install -c conda-forge -c bioconda pip rawtools maxquant=2.0.3.0 mono=5

# To activate this environment, use:
# 
#     micromamba activate /miniforge
# 
# Or to execute a single command in this environment, use:
# 
#     micromamba run -p /miniforge mycommand

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY ./lib/lrg-omics /lrg-omics

RUN cd /lrg-omics && pip install -e .

RUN chown 1000:1000 /data /compute /static /appmedia /datalake

COPY ./app /app

WORKDIR /app/

RUN dotnet --list-runtimes

