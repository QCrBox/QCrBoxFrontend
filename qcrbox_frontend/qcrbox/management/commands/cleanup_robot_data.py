from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group

from core import settings

class Command(BaseCommand):
    '''Config for the Command class'''

    def handle(self, *args, **options):

        # Cleanup any robot users, marked with username prefixes of _ROBOT_
        robot_users = User.objects.filter(username__startswith='_ROBOT_')
        
        if not robot_users.exists():
            raise ValueError('No robot users to delete!')

        for user in robot_users:
            user.delete()

        # Cleanup any robot groups, marked with name prefixes of _ROBOT_
        for group in Group.objects.filter(name__startswith='_ROBOT_'):

            group.delete()
