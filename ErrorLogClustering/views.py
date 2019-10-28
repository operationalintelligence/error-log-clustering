import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from log_cluster import cluster_pipeline

from Reader import reader


def index(request):
    return render(request, 'index.html')

@csrf_exempt
def api(request):
    if request.method == 'POST':
        data = {}
        request_params = json.loads(request.body)
        read = reader.ESReader(dict(request_params['query_settings']))
        df = read.execute()
        cluster = cluster_pipeline.Cluster(df, 'INDEX', request_params['cluster_settings'],
                                           request_params['query_settings'])
        clustered_df = cluster.process()
        data['clustered_df'] = clustered_df

    return JsonResponse(data, safe=False)
