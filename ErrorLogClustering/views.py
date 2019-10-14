from django.http import JsonResponse
from django.views import View
from ESReader.forms import ESReaderForm
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.shortcuts import redirect, reverse
from django.http import HttpResponse


def main(request):
    return render(request, 'index.html')
