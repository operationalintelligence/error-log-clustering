from django.urls import path, re_path

from Clustering.views import LogClustering

urlpatterns = [
    re_path(r'^process/$', LogClustering.as_view(), name="get"),
    # path('process', LogClustering.as_view(), name='get'),
]
