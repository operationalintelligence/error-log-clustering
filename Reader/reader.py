from ErrorLogClustering.settings import ES_HOSTS, ES_USER, ES_PASSWORD, ES_INDEX, DEBUG
from elasticsearch import Elasticsearch
import pandas as pd

STEP_SIZE_DEFAULT = 1000
TIMEOUT = '20m'

class ESReader(object):

    if ES_USER and ES_PASSWORD:
        es_connection = Elasticsearch(hosts=ES_HOSTS, http_auth=(ES_USER, ES_PASSWORD))
    else:
        es_connection = Elasticsearch(hosts=ES_HOSTS)

    def __init__(self, query, index):
        self.es_query = query
        self.size = 0
        self.index = index

    def execute(self):
        data = []
        for entry in self.scrolling(self.es_query):
            data.append(entry)
        self.es_results = data
        self.size = len(data)
        return pd.DataFrame(data).set_index(self.index)

    def scrolling(self, query):
        is_first = True
        while True:
            # Scroll next
            if is_first:  # Initialize scroll
                result = self.es_connection.search(index=ES_INDEX,
                                                   body=query,
                                                   scroll=TIMEOUT,
                                                   size=STEP_SIZE_DEFAULT)
                is_first = False
            else:
                result = self.es_connection.scroll(body={
                    "scroll_id": scroll_id,
                    "scroll": TIMEOUT
                })
            scroll_id = result["_scroll_id"]
            hits = result["hits"]["hits"]
            scroll_size = len(hits)
            if not hits:
                break
            for item in hits:
                yield item["_source"]


