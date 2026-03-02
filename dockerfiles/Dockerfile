FROM ubuntu:24.04

SHELL ["/bin/bash", "-c"]

ENV PYTHONUNBUFFERED=1

RUN mkdir /data /compute /static /appmedia /datalake

# Get OS version info
RUN cat /etc/os-release

RUN apt-get update && \
    apt-get install -y build-essential time curl wget libicu-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh

RUN chmod +x Miniforge3-Linux-x86_64.sh && bash Miniforge3-Linux-x86_64.sh -b -p /opt/conda \
    && rm -f Miniforge3-Linux-x86_64.sh

# Downgrade conda python to python 3.10
RUN /opt/conda/bin/conda install -y python=3.10

# allow running dotnet without ICU globalization data if needed
ENV DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1

# install .NET Core runtimes so MaxQuantCmd.exe dependencies are available
RUN curl -SL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh \
    && chmod +x /tmp/dotnet-install.sh \
    && /tmp/dotnet-install.sh --channel 2.1 --install-dir /usr/share/dotnet \
    && /tmp/dotnet-install.sh --channel 3.1 --install-dir /usr/share/dotnet \
    && /tmp/dotnet-install.sh --version 8.0.302 --install-dir /usr/share/dotnet \
    && ln -sf /usr/share/dotnet/dotnet /usr/bin/dotnet \
    && rm /tmp/dotnet-install.sh

# add uv package really fast for installations; override channels to avoid TOS prompts
# Note: mono may not be available on ARM64, install what's available
RUN /opt/conda/bin/conda install --override-channels -c conda-forge -c bioconda pip uv || true
RUN /opt/conda/bin/conda install --override-channels -c conda-forge -c bioconda rawtools || true
RUN /opt/conda/bin/conda install --override-channels -c conda-forge -c bioconda mono || true

COPY requirements.txt requirements.txt

# add this to avoid issues with matplotlib installation
ENV MPLCONFIGDIR=/tmp/matplotlib

# add uv to install with increased timeout for large packages
ENV UV_HTTP_TIMEOUT=300
RUN /opt/conda/bin/uv pip install --python /opt/conda/bin/python --no-cache -r requirements.txt

RUN chown 1000:1000 /data /compute /static /appmedia /datalake

COPY ./app /app

# ensure plotly asset is available locally for dash (even without collectstatic)
RUN mkdir -p /app/main/static/dash/component_data/plotly/package_data \
    && cp /opt/conda/lib/python3.10/site-packages/plotly/package_data/plotly.min.js \
         /app/main/static/dash/component_data/plotly/package_data/plotly.min.js

WORKDIR /app/

RUN dotnet --list-runtimes
