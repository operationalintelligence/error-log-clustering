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
        self.gte = request.GET.get('gte', '2019-09-01T00:00:00.000Z')
        self.lte = request.GET.get('lte', '2019-09-02T00:00:00.000Z')
        self.error_type = request.GET.get('error_type', ['exeerrordiag'])
        self.page_size = request.GET.get('page_size', 10000)

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
                'size': self.page_size,
                '_source': self.error_type,
                'query':{
                    'bool': {
                        'must': [
                            {'term': {'jobstatus': 'failed'}},
                            {
                                'range': {
                                    'starttime': {
                                        'gte': self.gte,
                                        'lte': self.lte
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
            if not hits:
                break
            for item in hits:
                yield item["_source"]

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