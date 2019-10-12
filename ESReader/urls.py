from django.urls import path, re_path

from ESReader.views import QueryES, DirectESReader

urlpatterns = [
    # re_path(r'^get/$', QueryES.as_view(), name="get"),
    path('', QueryES.as_view(), name="get"),
    re_path(r'^direct/$', DirectESReader.as_view(), name="get")
    # path('search', QueryES.as_view(), name="post"),
    # path('get', QueryES.as_view(), name="get"),
]
