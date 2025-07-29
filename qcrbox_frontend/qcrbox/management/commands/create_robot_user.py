'''A command to automatically create a user account with a specified role,
for use in automated robot framework test suites.

Invoke with:
`python manage.py create_robot_user [username] [email] [password] [role]`

where 'role' is one of 'admin', 'global manager', 'group manager' or 'user'.

'''

import logging
from django.contrib.auth.models import User, Permission
from django.core.management.base import BaseCommand

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
