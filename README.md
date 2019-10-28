# Error log clustering

## Short description
The tool is built on Django and ElasticSearch as data source.
It provides abilities for error logs clusterization using web-interface or as a service.

Web-service mode:
-------------------
data.json

{"source": "ES",
	"query_settings": {
		"start_date": "01.10.2019T00:00:000Z",
		"end_date": "01.10.2019T01:00:000Z",
		"error_type": "exeerror",
		"page_size": 1000,
		"index": pandaid,
		"target": "exeerrordiag"
	},
	"cluster_settings": {
		"w2v_size": 300,
		"w2v_window": 10,
		"min_samples": 1,
		"tokenize": "nltk"
	}
}

curl -H "Accept: application/json" -H "Content-Type: application/json" -X POST http://localhost:8000/cluster_api/ -d "@data.json"


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