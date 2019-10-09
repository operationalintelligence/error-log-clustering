from django.urls import path

from Clustering.views import LogClustering

urlpatterns = [
    path('process', LogClustering.as_view(), name='get'),
]
