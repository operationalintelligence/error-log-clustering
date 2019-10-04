import json
import os
import sys

from django.views import View
from django.http import JsonResponse
from elasticsearch import Elasticsearch

from ErrorLogClustering.settings import ES_HOSTS, ES_USER, ES_PASSWORD, ES_INDEX, DEBUG


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
        query = self.prepare_query(request)
        if query["status"]:
            es_data = self.get_from_es(query=query["body"])
            if es_data["status"]:
                data = self.process_gotten_data(es_data=es_data["es_data"])
            else:
                data = es_data
        else:
            data = query

        return JsonResponse(data)

    @track_error
    def prepare_query(self, request):
        data = {}

        raw_query = request.GET.get("query")
        if not raw_query:
            query = {
                "query": {
                    "match_all": {}
                }
            }
        else:
            query = json.loads(raw_query)

        # Customize query here with data by default e.g., sort, size, etc.

        data["body"] = query

        return data

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
    def process_gotten_data(self, es_data):
        data = {}

        # Data process here for e.g.
        data["es_data"] = es_data

        return data
