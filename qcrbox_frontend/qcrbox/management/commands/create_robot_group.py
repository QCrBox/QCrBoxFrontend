'''A command to create a group and assign members to it, for use in automated
robot framework test suites. Groups are managed in lldap in production (and
mirrored into Django on login); this command replaces the removed frontend
group-management UI for test seeding.

Invoke with:
`python manage.py create_robot_group [name] [member_username ...]`

'''

import logging

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
    '''Config for the Command class'''

    def add_arguments(self, parser):
        parser.add_argument('name', type=str)
        parser.add_argument('members', type=str, nargs='*')

    def handle(self, *args, **options):
        name = options['name']

        group, created = Group.objects.get_or_create(name=name)
        LOGGER.info(
            'Group %s %s for testing.',
            name,
            'created' if created else 'already exists; reusing',
        )

        for username in options['members']:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                LOGGER.error('Cannot add %s to group %s: no such user!', username, name)
                raise
            group.user_set.add(user)
            LOGGER.info('Added user %s to group %s.', username, name)
