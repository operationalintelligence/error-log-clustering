# Error log clustering

## Short description
The tool is built on Django and ElasticSearch as data source.
It provides abilities for error logs clusterization using web-interface or as a service.

## Requirements
```
python >= 3.6
ClusterLogs==0.0.3
Django==2.2.6
elasticsearch==7.0.5
fuzzywuzzy==0.17.0
gensim==3.8.1
kneed==0.5.0
matplotlib==3.0.3
nltk==3.4.5
numpy==1.16.2
pandas==0.24.2
pyonmttok==1.10.1
scikit-learn==0.20.3
scipy==1.2.1
```

## Installation from Docker
1) run docker (this command is automatically downloads (pulls) image that doesn't exist locally, creates a container and starts it)
```
docker run -p 80:80 -it operationalintelligence/error-log-clustering bash
```
2) in docker bash - set configuration in (*config.ini*) file in /config directory:
```
vi config/config.ini
```
In *config.ini* specify secret key, connection settings to the ElasticSearch instance, and index to work with.
```
SECRET_KEY:&y&s3(9b0hvuxi)&ab80grj*^lpd@5665xnu&e+kqq=%+&wn^6
ES_HOSTS:http://localhost:9200/
ES_USER:admin
ES_PASSWORD:123456
ES_INDEX:my-es-index
ALLOWED_HOSTS:*
```
Save file and close it (:wq).
3) Start Django server
```
./run.sh
```

Web-service mode:
-------------------
1) On a local machine create file with the default (recommended) settings

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
	"cluster_settings": {
		"w2v_size": 300,
		"w2v_window": 10,
		"min_samples": 1,
		"tokenizer": "nltk"
	},
	"index": "pandaid",
	"target": "exeerrordiag",
	"query_results": false,
	"calculate_statistics": true,
	"mode": "INDEX",
	"timings": true
}
```
2) Execute CURL request in a new terminal window:
```
curl -H "Accept: application/json" -H "Content-Type: application/json" -X POST http://localhost:8000/cluster_api/ -d "@data.json"
```

Query string parameters:

- es_query - arbitrary ElasticSearch query, that must contain (at least) field with error messages
(without NaNs), and field with unique ID (in the case of `ES@Chicago/jobs_archive` is can be `'exeerrordiag','pandaid'`)

- cluster_settings:
  - `w2v_size` - number of dimensions for vector (in most cases recommended 100-300)
  - `w2v_window` - size of slicing window for NN algorithms (recommended >= 5)
  - `min_samples` - min. size of cluster (recommended 1)
  - `tokenizer` - 'nltk' | 'pyonmttok' (recommended 'nltk')

- `index` - index field (i.e, `'pandaid'`)
- `target` - field containing error messages (i.e. `'exeerrordiag'`)
- `query_results` - if true, then ES response will be printed in the output JSON
- `calculate_statistics` - if true, statistics of all clusters will be printed
- `mode` - options ALL | INDEX
  - if `ALL` - the results of clusterization will be represented as a dictionary, with lists of all values
  - if `INDEX` - a list of IDs for each cluster
  - if `TARGET` - a list of error messages for each cluster
- `timings` - output timings for each stage of clusterization pipeline
