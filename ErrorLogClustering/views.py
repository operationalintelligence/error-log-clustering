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
            mode = req.get('mode')
            stat = req.get('calculate_statistics')

            try:

                read = reader.ESReader(req.get('es_query'))
                df = read.execute()

                if req['query_results'] == True:
                    data['es_results'] = read.es_results

                try:

                    cluster = cluster_pipeline.Cluster(df,
                                                       mode,
                                                       req['cluster_settings'],
                                                       req['query_settings'])
                    clustered_df = cluster.process()

                    if stat and mode == 'ALL':
                        statistics = cluster.statistics(clustered_df)
                        data['statistics'] = statistics
                    data['clustered_df'] = clustered_df
                    data['timings'] = cluster.timings
                    data['number_of_records'] = read.size

                except Exception as e:

                    data['error'] = str(e)

            except Exception as e:

                data['error'] = str(e)

        except Exception as e:

            data['error'] = str(e)

    return JsonResponse(data, safe=False)
