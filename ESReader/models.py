from django.db import models

class Errors(models.Model):
    error_message = models.CharField(max_length=1000)
    cluster_label = models.IntegerField(default=0)
