from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from core import settings

class Command(BaseCommand):

    def handle(self, *args, **options):

        # If no users exist
        if User.objects.count() == 0:

            # Fetch admin account details from settings
            username = settings.ADMIN_ACCOUNT
            email = settings.ADMIN_EMAIL
            password = settings.ADMIN_PASSWORD

            # Fail if the deployer forgot to re-set the default password
            if password == 'None':
                print('WARNING: No ADMIN_PASSWORD set in settings.py!  No admin user created!')

            # Create the admin
            else:
                print('Creating admin account for "'+username+'"')
                admin = User.objects.create_superuser(email=email, username=username, password=password)
                admin.is_active = True
                admin.is_admin = True
                admin.is_staff = True

                admin.save()

        # Fail if ANY users already exist in the db
        else:
            print('Users already present in database; no admin account created.')
