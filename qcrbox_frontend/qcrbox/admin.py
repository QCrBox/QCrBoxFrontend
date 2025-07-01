'''QCrBox Admin

Module containing classes which register the various models in models.py
with the django admin view.

'''

from django.contrib import admin
from . import models

@admin.register(models.FileMetaData)
class FileMetaDataAdmin(admin.ModelAdmin):
    '''Admin Registration for the FileMetaData model'''

    list_display = ('filename', 'user', 'group')
    ordering = ('filename', 'backend_uuid')

@admin.register(models.ProcessStep)
class ProcessStepAdmin(admin.ModelAdmin):
    '''Admin Registration for the ProcessStep model'''

    list_display = ('infile', 'application', 'outfile')
    ordering = ('infile', 'application', 'outfile')

@admin.register(models.Application)
class ApplicationAdmin(admin.ModelAdmin):
    '''Admin Registration for the Application model'''

    list_display = ('name', 'version')
    ordering = ('name', 'version')

@admin.register(models.SessionReference)
class SessionReferenceAdmin(admin.ModelAdmin):
    '''Admin Registration for the SessionReference model'''

    list_display = ('application', 'session_id', 'user')
    ordering = ('start_time',)
