import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from clusterlogs import pipeline

from Reader import reader


def index(request):
    return render(request, 'index.html')

@csrf_exempt
def api(request):
    data = {}
    if request.method == 'POST':
        try:
            req = json.loads(request.body)
            index = req.get('index')
            target = req.get('target')
            mode = req.get('mode')
            stat = req.get('calculate_statistics')
            timings = req.get('timings')
            query = req.get('es_query')
            cluster_settings = req.get('cluster_settings')

            try:

                read_handler = reader.ESReader(query, index)
                df = read_handler.execute()

                data['query'] = read_handler.es_query
                data['number_of_records'] = read_handler.size

                if req['query_results'] == True:
                    data['es_results'] = read_handler.es_results

                try:

                    cluster = pipeline.ml_clustering(df, target, cluster_settings)

                    cluster.process()

                    if stat:
                        data['statistics'] = cluster.statistics()

                    if timings:
                        data['timings'] = cluster.timings

                    data['clustered_df'] = cluster.clustered_output(mode)
                    data['clusterization_parameters'] = cluster_settings

                except Exception as e:

                    data['error'] = str(e)

            except Exception as e:

                data['error'] = str(e)

        except Exception as e:

            data['error'] = str(e)

    return JsonResponse(data, safe=False)
