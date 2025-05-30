from django.db import models
from django.contrib.auth.models import User, Group

# Create your models here.

class FileMetaData(models.Model):
    filename = models.CharField(max_length=255)
    backend_uuid = models.CharField(max_length=255, null=True)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)

class ProcessStep(models.Model):
    application = models.CharField(max_length=255, blank=True, null=True,)
    infile = models.ForeignKey(FileMetaData, null=True, on_delete=models.SET_NULL, related_name='processed_to')
    outfile = models.ForeignKey(FileMetaData, null=True, on_delete=models.SET_NULL, related_name='processed_by')
