FROM python:3.7

ENV PYTHONUNBUFFERED 1

RUN mkdir /ErrorLogClustering
WORKDIR /ErrorLogClustering
ADD . /ErrorLogClustering/

RUN pip install -r requirements.txt