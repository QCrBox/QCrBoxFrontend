from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from core import settings

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
            raise ValueError('User already exists in database!')

        # Fetch user account details from settings
        username = username
        email = email
        password = password

        user = User.objects.create_superuser(
            email=email,
            username=username,
            password=password,
        )

        if options['role'].lower() == 'admin':

            user.is_active = True
            user.is_admin = True
            user.is_staff = True

        user.save()
