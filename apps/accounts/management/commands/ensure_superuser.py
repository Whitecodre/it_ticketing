import os
from django.core.management.base import BaseCommand
from apps.accounts.models import User

class Command(BaseCommand):
    help = 'Creates a superuser if one does not exist'

    def handle(self, *args, **options):
        email = os.environ.get('SUPERUSER_EMAIL')
        password = os.environ.get('SUPERUSER_PASSWORD')
        if not email or not password:
            self.stderr.write("SUPERUSER_EMAIL and SUPERUSER_PASSWORD must be set.")
            return

        if User.objects.filter(role=User.Role.SUPERADMIN).exists():
            self.stdout.write("Superuser already exists. Nothing to do.")
            return

        User.objects.create_superuser(
            email=email,
            password=password,
            first_name='Super',
            last_name='Admin',
            department='IT',
        )
        self.stdout.write(f"Superuser {email} created.")