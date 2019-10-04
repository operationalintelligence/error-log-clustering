FROM python:3.6

ENV PYTHONUNBUFFERED 1

RUN mkdir /ErrorLogClustering
WORKDIR /ErrorLogClustering
ADD . /ErrorLogClustering/

RUN pip install -r requirements.txt