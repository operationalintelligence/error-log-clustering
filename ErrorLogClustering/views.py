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
    data = {}
    if request.method == 'POST':
        try:
            req = json.loads(request.body)
            index = req.get('index')
            target = req.get('target')
            mode = req.get('mode')
            stat = req.get('calculate_statistics')

            try:

                read_handler = reader.ESReader(req.get('es_query'))
                df = read_handler.execute()

                data['query'] = read_handler.es_query
                data['number_of_records'] = read_handler.size

                if req['query_results'] == True:
                    data['es_results'] = read_handler.es_results

                try:

                    cluster = cluster_pipeline.Cluster(df,
                                                       index,
                                                       target,
                                                       mode,
                                                       req['cluster_settings'])
                    clustered_df = cluster.process()

                    if stat and mode == 'ALL':
                        statistics = cluster.statistics(clustered_df)
                        data['statistics'] = statistics
                    data['clustered_df'] = clustered_df
                    data['clusterization_parameters'] = req.get('cluster_settings')
                    data['timings'] = cluster.timings

                except Exception as e:

                    data['error'] = str(e)

            except Exception as e:

                data['error'] = str(e)

        except Exception as e:

            data['error'] = str(e)

    return JsonResponse(data, safe=False)
