from django.contrib import admin
from .models import *

@admin.register(FileMetaData)
class FileMetaDataAdmin(admin.ModelAdmin):
    list_display=('filename','user','group')
    ordering=('filename','backend_uuid')

@admin.register(ProcessStep)
class ProcessStepAdmin(admin.ModelAdmin):
    list_display=('infile','application','outfile')
    ordering=('infile','application','outfile')

@admin.register(Application)
class ProcessStepAdmin(admin.ModelAdmin):
    list_display=('name','version')
    ordering=('name','version')