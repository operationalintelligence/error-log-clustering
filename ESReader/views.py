import os
import sys
from django.views import View
from django.http import JsonResponse
from elasticsearch import Elasticsearch
from django.shortcuts import render
from .forms import ESReaderForm
import json
from ErrorLogClustering.settings import ES_HOSTS, ES_USER, ES_PASSWORD, ES_INDEX, DEBUG
from .models import Errors, ReaderSettings

STEP_SIZE_DEFAULT = 1000
TIMEOUT = '20m'


def safe_run(func):
    def func_wrapper(*args, **kwargs):

        try:
            return func(*args, **kwargs)

        except Exception as e:

            print(e)
            return None

    return func_wrapper


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
    model = Errors

    def get_session_id(self, request):
        """
        Safe session_id getter
        :param request:
        :return:
        """
        if not request.session.session_key:
            request.session.create()
        return request.session.session_key

    def get(self, request, *args, **kwargs):
        self.session_id = self.get_session_id(request)
        try:
            data = self.get_from_model()
            if (data['empty'] == False):
                # data['reader_form'] = request.session.get('reader_form')
                data['submitted'] = True
                return render(request, self.template_name, data)
            else:
                return render(request, self.template_name, {'form': self.form_class()})
        except Exception as e:
            return render(request, self.template_name, {'form': self.form_class()})

    def post(self, request, *args, **kwargs):
        self.session_id = self.get_session_id(request)
        form = self.form_class(request.POST)
        if form.is_valid():
            try:
                self.delete_from_model()
                #
                # request.session['reader_form'] = form.cleaned_data
                request.session['source'] = 'ES@Chicago'

                self.start_date = form.cleaned_data['start_date']
                self.end_date = form.cleaned_data['end_date']
                self.error_type = form.cleaned_data['error_type']
                self.page_size = form.cleaned_data['page_size']

                query = self.prepare_query(request)

                if query["status"]:
                    es_data = []
                    # ElasticSearch Scrolling...
                    for entry in self.scrolling(query=query["body"]):
                        es_data.append(entry)
                    # Save to Django model
                    self.save_to_model(es_data=es_data, settings=form.cleaned_data)
                    data = self.get_from_model()
                else:
                    data = query

                data['settings'] = form.cleaned_data
                data['submitted'] = True
                return render(request, self.template_name, data)
            except Exception as e:
                return render(request, self.template_name, {'form': form})
        else:
            return render(request, self.template_name, {'form': form})

    @track_error
    def prepare_query(self, request):
        data = {}

        raw_query = request.GET.get("query")
        if not raw_query:
            query = {
                'size': self.page_size,
                '_source': ['pandaid', 'starttime', self.error_type + 'code', self.error_type + 'diag'],
                'query': {
                    'bool': {
                        'must': [
                            {
                                "exists": {
                                    "field": self.error_type + 'diag'
                                }
                            },
                            {'term': {'jobstatus': 'failed'}},
                            {
                                'range': {
                                    'starttime': {
                                        'gte': self.start_date,
                                        'lte': self.end_date
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        else:
            query = json.loads(raw_query)

        data["body"] = query

        return data

    @safe_run
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

    @safe_run
    def save_to_model(self, es_data, settings):
        """
        Save error logs data from ES to Django model Errors
        :param es_data:
        :return:
        """
        reader_settings = ReaderSettings()
        reader_settings.start_date = settings['start_date']
        reader_settings.end_date = settings['end_date']
        reader_settings.error_type = settings['error_type']
        reader_settings.page_size = settings['page_size']
        reader_settings.session_id = self.session_id
        reader_settings.save()

        for item in es_data:
            m = Errors.objects.create(pandaid=item['pandaid'],
                                      modificationtime=item['starttime'],
                                      error_type=self.error_type,
                                      error_code=item[self.error_type + 'code'],
                                      error_message=item[self.error_type + 'diag'],
                                      session_id=self.session_id)
            m.save()

    @track_error
    def get_from_model(self):
        """
        Get data from Errors model for current user session
        :return:
        """
        data = {}
        data['es_data'] = [entry for entry in Errors.objects.filter(session_id=self.session_id)
            .values('pandaid', 'modificationtime', 'error_code', 'error_message')]
        data['settings'] = [entry for entry in ReaderSettings.objects.filter(session_id=self.session_id)\
            .values('start_date','end_date','error_type','page_size')][0]
        if len(data['es_data']) == 0 or len(data['settings']) == 0:
            data = {}
            data['empty'] = True
        else:
            data['empty'] = False
        return data

    @safe_run
    def delete_from_model(self):
        """
        Delete from Errors model all records for current user session
        :return:
        """
        query = Errors.objects.filter(session_id=self.session_id)
        query.delete()
        settings = ReaderSettings.objects.filter(session_id=self.session_id)
        settings.delete()


class DirectESReader(QueryES):
    def get(self, request, *args, **kwargs):
        self.session_id = self.get_session_id(request)
        self.start_date = request.GET.get('start_date', '2019-09-01T00:00:00.000Z')
        self.end_date = request.GET.get('end_date', '2019-09-01T05:00:00.000Z')
        self.error_type = request.GET.get('error_type', 'exeerror')
        self.page_size = request.GET.get('page_size', 10000)

        request.session['settings'] = {'start_date': self.start_date,
                                       'end_date': self.end_date,
                                       'error_type': self.error_type,
                                       'paghe_size': self.page_size}

        self.delete_from_model()
        query = self.prepare_query(request)
        if query["status"]:
            es_data = []
            for entry in self.scrolling(query=query["body"]):
                es_data.append(entry)
            data = self.save_to_model(es_data=es_data)
        else:
            data = query
        return JsonResponse(data)
