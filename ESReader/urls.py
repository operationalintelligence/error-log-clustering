from django.urls import path, re_path

from ESReader.views import QueryES

urlpatterns = [
    re_path(r'^get/$', QueryES.as_view(), name="get"),
    # path('get', QueryES.as_view(), name="get"),
]
