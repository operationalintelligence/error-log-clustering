# Error log clustering

## Short description
The tool is built on Django and ElasticSearch as data source.
The tool ....


## Configuration
To configure ElasticSearch you need to drop config file (*config.ini*) to **/** directory with following structure:
```
SECRET_KEY:&y&s3(9b0hvuxi)&ab80grj*^lpd@5665xnu&e+kqq=%+&wn^6
ES_HOSTS:http://localhost:9200/
ES_USER:admin
ES_PASSWORD:123456
ES_INDEX:my-es-index
```
## Requirements
```
Django==2.2.5
elasticsearch==7.0.4
pytz==2019.2
urllib3==1.25.3
```