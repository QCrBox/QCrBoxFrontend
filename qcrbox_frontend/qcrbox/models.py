from django.db import models
from django.contrib.auth.models import User, Group

# Create your models here.

class process_step(models.Model):
    application = models.CharField(max_length=255,)
    infile_uuid = models.CharField(max_length=255,)
    outfile_uuid = models.CharField(max_length=255, blank=True, null=True,)
    parent = models.ForeignKey("self", null=True, on_delete=models.SET_NULL,)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL,)
    group = models.ForeignKey(Group, on_delete=models.CASCADE,)