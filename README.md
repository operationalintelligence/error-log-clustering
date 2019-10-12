# Error log clustering

## Short description
The tool is built on Django and ElasticSearch as data source.
It provides abilities for error logs clusterization using web-interface or as a service.

Web-service mode:
-------------------
Endpoint 1 - ESReader (read data from ElasticSearch@Chicago and save it in local storage on server)

        /read_es?gte=<start_date>&lte=<end_date>&error_type=<exeerror|ddmerror|...>&page_size=<page_size>


Endpoint 2 - LogClustering (cluster data from the local storage and returns the result as JSON resporce)

        /cluster/direct?tokenizer=<nltk|pyonmttok>&w2v_size=<word2vec vector size>&w2v_window=<word2vec slicing window size>&min_samples=<for DBSCAN>

Web-interface mode:
-------------------
1) Upload from ES@Chicago

    Allows to upload data from ES@chicago and explore it using DataTables

2) Clusterization:

    Implements clusterization of data from the local storage

    Allows to explore cluster statistics and investirage all error messages within selected cluster

Note:

Current release doesn't provide concurrent users. It will be fixed in the next release.


## Configuration
To configure ElasticSearch you need to drop config file (*config.ini*) to **/** directory with following structure:
```
SECRET_KEY:&y&s3(9b0hvuxi)&ab80grj*^lpd@5665xnu&e+kqq=%+&wn^6
ES_HOSTS:http://localhost:9200/
ES_USER:admin
ES_PASSWORD:123456
ES_INDEX:my-es-index
ALLOWED_HOSTS:*
```
## Requirements
```
Django==2.2.5
elasticsearch==7.0.4
pytz==2019.2
urllib3==1.25.3
```