import json
import os
import sys

from django.views import View
from django.http import JsonResponse
from elasticsearch import Elasticsearch
from django.http import HttpResponseRedirect
from django.shortcuts import render, render_to_response
from django.shortcuts import redirect
from django.http import HttpResponse
from django.views.generic.edit import FormView
from .forms import ESReaderForm
import json


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

    template_name = 'reader.html'
    form_class = ESReaderForm
    success_url = 'search'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {'form': self.form_class})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if request.POST.get("submitted"):
            return render(request, self.template_name, {'form': form})
        if form.is_valid():
            self.gte = form.cleaned_data['start_date']
            self.lte = form.cleaned_data['end_date']
            self.error_type = form.cleaned_data['error_type']
            self.page_size = form.cleaned_data['page_size']

            self.delete_everything()
            query = self.prepare_query(request)
            print(query)
            if query["status"]:
                es_data = []
                for entry in self.scrolling(query=query["body"]):
                    es_data.append(entry)
                print(es_data)
                data = self.process_data(es_data=es_data)
            else:
                data = query

            data['reader_form'] = form.cleaned_data
            data['form'] = form
            data['submitted'] = True
            print(data)
            # return JsonResponse(data)
            return render(request, self.template_name, data)

        return render(request, self.template_name, {'form': form})

    @track_error
    def prepare_query(self, request):
        data = {}

        raw_query = request.GET.get("query")
        if not raw_query:
            query = {
                'size': self.page_size,
                '_source': ['pandaid', 'starttime', self.error_type+'code', self.error_type+'diag'],
                'query':{
                    'bool': {
                        'must': [
                            {
                                "exists": {
                                    "field": self.error_type+'diag'
                                }
                            },
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
            print(query)
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
        for item in es_data:
            m = Errors.objects.create(pandaid = item['pandaid'],
                                      modificationtime = item['starttime'],
                                      error_type = self.error_type,
                                      error_code = item[self.error_type+'code'],
                                      error_message = item[self.error_type+'diag'])
            m.save()
            data["es_data"] = [entry for entry in Errors.objects.all().values()]
        return data

    def delete_everything(self):
        Errors.objects.all().delete()

class DirectESReader(QueryES):

    def get(self, request, *args, **kwargs):
        if request.method == "GET":
            self.gte = request.GET.get('gte', '2019-09-01T00:00:00.000Z')
            self.lte = request.GET.get('lte', '2019-09-01T05:00:00.000Z')
            self.error_type = request.GET.get('error_type', 'exeerror')
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