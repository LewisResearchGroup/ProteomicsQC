FROM continuumio/miniconda3:latest

# Downgrade conda python to python 3.10
RUN conda install -y python=3.10

RUN cat /etc/os-release

ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y build-essential time curl libicu-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN python --version

# allow running dotnet without ICU globalization data if needed
ENV DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1

# install .NET Core runtimes so MaxQuantCmd.exe dependencies are available
RUN curl -SL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh \
    && chmod +x /tmp/dotnet-install.sh \
    && /tmp/dotnet-install.sh --channel 2.1 --install-dir /usr/share/dotnet \
    && /tmp/dotnet-install.sh --channel 3.1 --install-dir /usr/share/dotnet \
    && /tmp/dotnet-install.sh --channel 8.0 --install-dir /usr/share/dotnet \
    && ln -sf /usr/share/dotnet/dotnet /usr/bin/dotnet \
    && rm /tmp/dotnet-install.sh

# add uv package really fast for installations; override channels to avoid TOS prompts
RUN conda install --override-channels -c conda-forge -c bioconda pip rawtools mono=5 uv

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

# ensure plotly asset is available locally for dash (even without collectstatic)
RUN mkdir -p /app/main/static/dash/component_data/plotly/package_data \
    && cp /opt/conda/lib/python3.10/site-packages/plotly/package_data/plotly.min.js \
         /app/main/static/dash/component_data/plotly/package_data/plotly.min.js

WORKDIR /app/
