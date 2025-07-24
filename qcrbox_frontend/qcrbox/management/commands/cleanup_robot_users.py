from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from core import settings

class Command(BaseCommand):
    '''Config for the Command class'''

    def add_arguments(self, parser):
        parser.add_argument('admin_account', type=str)
        parser.add_argument('user_account', type=str)

    def handle(self, *args, **options):
        for username in (options['admin_account'], options['user_account']):

            # If user exists, delete
            user = User.objects.get(username=username)
            user.delete()
