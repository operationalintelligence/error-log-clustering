from django.urls import path, re_path

from Clustering.views import LogClustering, LogClusteringService

urlpatterns = [
    re_path(r'^process/$', LogClustering.as_view(), name="get"),
    # path('process/<int:cluster>/', LogClustering.as_view(), name = "explore"),
    re_path(r'^direct/$', LogClusteringService.as_view(), name="get")
    # path('process', LogClustering.as_view(), name='get'),
]
