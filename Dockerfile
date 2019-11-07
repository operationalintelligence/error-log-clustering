FROM python:3.7

ENV PYTHONUNBUFFERED 1

RUN mkdir /exit;
WORKDIR /ErrorLogClustering
ADD . /ErrorLogClustering/

RUN pip install -r requirements.txt

RUN chmod +x run.sh

RUN apt-get update

RUN apt-get install vim

RUN mkdir config

RUN touch config/config.ini