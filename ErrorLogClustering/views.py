from django.http import JsonResponse
from django.views import View
from ESReader.forms import ESReaderForm
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.shortcuts import redirect, reverse
from django.http import HttpResponse


def main(request):
    return render(request, 'index.html')
        # return HttpResponseRedirect('/read_es/')
    # if request.POST.get('submitted'):
    #     return JsonResponse(request)
    # else:
    #     return redirect('reader_form')


# def reader_form(request):
#     # if this is a POST request we need to process the form data
#     if request.method == 'POST':
#         # create a form instance and populate it with data from the request:
#         form = ESReaderForm(request.POST)
#         # check whether it's valid:
#         if form.is_valid():
#             data = {}
#             print("form is valid")
#             data['start_date'] = form.cleaned_data['start_date']
#             data['end_date'] = form.cleaned_data['end_date']
#             data['error_type'] = form.cleaned_data['error_type']
#             data['page_size'] = form.cleaned_data['page_size']
#             data['submitted'] = True
#             return JsonResponse(data)
#
#     # if a GET (or any other method) we'll create a blank form
#     else:
#         form = ESReaderForm()
#
#     return render(request, 'index.html', {'form': form})