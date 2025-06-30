'''QCrBox Apps

Config for installed django apps

'''

from django.apps import AppConfig

class QcrboxConfig(AppConfig):
    '''Config for the QCrBox app (default django app for this project)'''

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'qcrbox'
