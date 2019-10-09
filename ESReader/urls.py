from django.urls import path

from ESReader.views import QueryES

urlpatterns = [
    path('get', QueryES.as_view(), name="get"),
]
