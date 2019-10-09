from django.urls import path

from CommunicatES.views import QueryES

urlpatterns = [
    path('get', QueryES.as_view(), name="get"),
]
