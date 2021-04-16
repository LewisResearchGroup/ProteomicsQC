FROM python:3
ENV PYTHONUNBUFFERED=1
RUN mkdir /data /compute /static /appmedia
WORKDIR /app
COPY requirements.txt /app/
RUN pip install -r requirements.txt
COPY . /app/
RUN pip install -e /app/lrg_omics