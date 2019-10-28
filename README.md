# Error log clustering

## Short description
The tool is built on Django and ElasticSearch as data source.
It provides abilities for error logs clusterization using web-interface or as a service.

Web-service mode:
-------------------
data.json

```
{
	"es_query": {
		"size": 100,
		"_source": ["pandaid", "exeerrorcode", "exeerrordiag", "starttime"],
		"query":{
			"bool": {
				"must": [
					{"exists": {"field": "exeerrordiag"}},
					{"term": {"jobstatus": "failed"}},
					{
						"range": {
							"starttime": {
								"gte": "2019-10-01T09:00:00.000Z",
								"lte": "2019-10-01T10:30:00.000Z"
							}
						}
					}
				]
			}
		}
	},
	"query_settings": {
		"index": "pandaid",
		"target": "exeerrordiag"
	},
	"cluster_settings": {
		"w2v_size": 300,
		"w2v_window": 10,
		"min_samples": 1,
		"tokenizer": "nltk"
	},
	"query_results": false,
	"calculate_statistics": true,
	"mode": "ALL"
}
```
CURL STRING:
```
curl -H "Accept: application/json" -H "Content-Type: application/json" -X POST http://localhost:8000/cluster_api/ -d "@data.json"
```

Query string parameters:

-- es_query - arbitrary ElasticSearch query, that must contain (at least) field with error messages
(without NaNs), and field with unique ID (in the case of ES@Chicago/jobs_archive is can be 'pandaid', 'exeerrordiag')

-- query_settings:
    -- index - index field (i.e, 'pandaid')
    -- target - field containing error messages (i.e. 'exeerrordiag')

-- cluster_settings:
   -- w2v_size - number of dimensions for vector
   -- w2v_window - size of slicing window for NN algorithms
   -- min_samples - min. size of cluster
   -- tokenizer - 'nltk'

-- query_results - if true, then ES response will be saved as output
-- calculate_statistics - if true, statistics of all clusters will be saved
-- mode - options ALL | INDEX
   -- if ALL - the results of clusterization will be represented as a dictionary, with lists of all values
   -- if INDEX - the results will be represetned as a list of IDs for each cluster

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