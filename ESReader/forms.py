from django import forms
import pickle

class ESReaderForm(forms.Form):
    start_date = forms.CharField(label='Start Date', max_length=100)
    end_date = forms.CharField(label='End Date', max_length=100)
    error_type = forms.CharField(label='Error Type', max_length=100)
    page_size = forms.CharField(label='Page Size', max_length=100)
