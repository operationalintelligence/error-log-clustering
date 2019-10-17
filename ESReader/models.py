from django.db import models
import datetime


class Errors(models.Model):
    pandaid = models.IntegerField(default=0, blank=True, null=True)
    modificationtime = models.CharField(max_length=100, blank=True, null=True,
                                        default=datetime.datetime.now().strftime('yyyy-mm-dd%H:%M:%S'))
    error_type = models.CharField(max_length=50, blank=True, null=True, default='')
    error_code = models.IntegerField(default=0, blank=True, null=True)
    error_message = models.CharField(max_length=5000, default='', blank=True, null=True)
    tokenized = models.CharField(max_length=6000, default='', blank=True, null=True)
    cluster_label = models.IntegerField(default=0, blank=True, null=True)
    session_id = models.CharField(blank=True, max_length=100, null=True, default='')

class ReaderSettings(models.Model):
    start_date = models.CharField(max_length=50, blank=True, null=True, default='')
    end_date = models.CharField(max_length=50, blank=True, null=True, default='')
    error_type = models.CharField(max_length=50, blank=True, null=True, default='')
    page_size = models.IntegerField(default=1000, blank=True, null=True)
    session_id = models.CharField(blank=True, max_length=100, null=True, default='')
