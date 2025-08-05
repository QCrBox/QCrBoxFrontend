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

    list_display = ('infile', 'command__app', 'command__name', 'outfile')
    ordering = ('infile', 'command__app', 'command__name', 'outfile')

@admin.register(models.Application)
class ApplicationAdmin(admin.ModelAdmin):
    '''Admin Registration for the Application model'''

    list_display = ('name', 'version')
    ordering = ('name', 'version')

@admin.register(models.AppCommand)
class AppCommand(admin.ModelAdmin):
    '''Admin Registration for the App Command model'''

    list_display = ('app', 'app__version', 'name')
    ordering = ('app', 'app__version', 'name')

@admin.register(models.CommandParameter)
class CommandParameter(admin.ModelAdmin):
    '''Admin Registration for the Command Parameter model'''

    list_display = ('command__app__name', 'command__app__version', 'command', 'name', 'dtype')
    ordering = ('command__app__name', 'command__app__version', 'command', 'name')

@admin.register(models.SessionReference)
class SessionReferenceAdmin(admin.ModelAdmin):
    '''Admin Registration for the SessionReference model'''

    list_display = ('application', 'session_id', 'user')
    ordering = ('start_time',)
