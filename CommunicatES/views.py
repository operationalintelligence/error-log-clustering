import json
import os
import sys

from django.views import View
from django.http import JsonResponse
from elasticsearch import Elasticsearch


from ErrorLogClustering.settings import ES_HOSTS, ES_USER, ES_PASSWORD, ES_INDEX, DEBUG
from .models import Errors

STEP_SIZE_DEFAULT = 1000
TIMEOUT = '20m'

def track_error(func):

    def wrapped(*args, **kwargs):
        data = {
            "status": True,
            "message": "Everything is fine!"
        }

        try:
            data.update(func(*args, **kwargs))
        except Exception as error:
            if DEBUG:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                file_name = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                message = {
                    "error": str(error),
                    "type": str(exc_type),
                    "filename": str(file_name),
                    "line_number": exc_tb.tb_lineno
                }
            else:
                message = {
                    "error": "Something went wrong on server side, your request failed!",
                    "type": "",
                    "filename": "",
                    "line_number": 0
                }

            data = {
                "status": False,
                "message": message
            }

        return data

    return wrapped


class QueryES(View):

    if ES_USER and ES_PASSWORD:
        es_connection = Elasticsearch(hosts=ES_HOSTS, http_auth=(ES_USER, ES_PASSWORD))
    else:
        es_connection = Elasticsearch(hosts=ES_HOSTS)

    def get(self, request):
        self.delete_everything()
        query = self.prepare_query(request)
        if query["status"]:
            es_data = []
            for entry in self.scrolling(query=query["body"]):
                es_data.append(entry)
            data = self.process_data(es_data=es_data)
        else:
            data = query

        return JsonResponse(data)

    @track_error
    def prepare_query(self, request):
        data = {}

        raw_query = request.GET.get("query")
        if not raw_query:
            query = {
                'size': 100000,
                '_source': ['exeerrordiag'],
                'query':{
                    'bool': {
                        'must': [
                            {'term': {'jobstatus': 'failed'}},
                            {
                                'range': {
                                    'starttime': {
                                        'gte': '2019-09-01T00:00:00.000Z',
                                        'lte': '2019-09-02T00:00:00.000Z'
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        else:
            query = json.loads(raw_query)

        # Customize query here with data by default e.g., sort, size, etc.

        data["body"] = query

        return data

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
            print(scroll_size)
            if not hits:
                break
            for item in hits:
                yield item["_source"]

    # def scrolling(self, query):
    #     data = {}
    #     output_list = []
    #     response = self.es_connection.search(index=ES_INDEX,
    #                              body=query,
    #                              scroll=TIMEOUT,
    #                              size=STEP_SIZE_DEFAULT)
    #
    #     for hit in response['hits']['hits']:
    #         output_list.append(hit['_source'])
    #
    #     size_limit = (STEP_SIZE_DEFAULT or response['hits']['total']) - len(output_list)
    #     if size_limit:
    #
    #         def _scroll_generator(client, scroll_id):
    #             r = client.scroll(scroll_id=scroll_id, scroll=TIMEOUT)
    #             while len(r['hits']['hits']) > 0:
    #                 for item in r['hits']['hits']:
    #                     yield item
    #                 r = client.scroll(scroll_id=scroll_id, scroll=TIMEOUT)
    #
    #         sid = response['_scroll_id']
    #
    #         for hit in _scroll_generator(client=self.es_connection, scroll_id=sid):
    #             output_list.append(hit['_source'])
    #             size_limit -= 1
    #             if not size_limit:
    #                 break

    @track_error
    def get_from_es(self, query):
        data = {}

        # Default data in track_error decorator
        # data["status"] is "True" if there is no error else False
        # data["message"] is "Everything is fine!" else error message

        es_data = self.es_connection.search(index=ES_INDEX, body=query)
        data["es_data"] = es_data

        # Customize your JSON response here, e.g.
        # data["time_elapsed"] = "0.1s"

        return data

    @track_error
    def process_data(self, es_data):
        data = {}
        errors = []
        for dic in es_data:
            for val in dic.values():
                errors.append(val)
        errors = list(filter(None, errors))
        data["es_data"] = errors
        for i in errors:
            p = Errors.objects.create(error_message=i)
            p.save()
        return data

    def delete_everything(self):
        Errors.objects.all().delete()