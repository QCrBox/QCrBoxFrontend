from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Permission
import logging

from core import settings

LOGGER = logging.getLogger(__name__)

class Command(BaseCommand):
    '''Config for the Command class'''

    def add_arguments(self, parser):
        parser.add_argument('username', type=str)
        parser.add_argument('email', type=str)
        parser.add_argument('password', type=str)
        parser.add_argument('role', type=str)

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']

        # If user already exists, skip
        if User.objects.filter(username=username).exists():
            LOGGER.error(
                'User %s could not be created: already exists!',
                username,
            )
            raise ValueError('User already exists in database!')

        # Fetch user account details from settings
        username = username
        email = email
        password = password

        LOGGER.info(
            'Creating User %s for testing.',
            username,
        )

        user = User.objects.create_user(
            email=email,
            username=username,
            password=password,
        )

        user.is_active = True

        if options['role'].lower() == 'admin':

            user.is_admin = True
            user.is_staff = True

            LOGGER.info(
                'User %s given role Admin.',
                username,
            )

        elif options['role'].lower() == 'global manager':

            user.user_permissions.add(Permission.objects.get(codename='edit_users'))
            user.user_permissions.add(Permission.objects.get(codename='edit_data'))
            user.user_permissions.add(Permission.objects.get(codename='global_access'))

            LOGGER.info(
                'User %s given role Global Manager.',
                username,
            )

        elif options['role'].lower() == 'group manager':

            user.user_permissions.add(Permission.objects.get(codename='edit_users'))
            user.user_permissions.add(Permission.objects.get(codename='edit_data'))

            LOGGER.info(
                'User %s given role Group Manager.',
                username,
            )

        user.save()
