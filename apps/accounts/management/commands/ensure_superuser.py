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

        # Check if any superuser already exists
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write("Superuser already exists. Nothing to do.")
            return

        # Create the superuser (this sets is_superuser=True, is_staff=True)
        user = User.objects.create_superuser(
            email=email,
            password=password,
            first_name='Super',
            last_name='Admin',
        )
        # If your User model has a 'role' field, set it to SUPERADMIN
        user.role = User.Role.SUPERADMIN
        user.save()
        self.stdout.write(f"Superuser {email} created.")