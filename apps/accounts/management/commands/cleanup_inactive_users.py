from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models import User

class Command(BaseCommand):
    help = 'Delete users that have been inactive for 90 days or more'

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=90)
        deleted, _ = User.objects.filter(
            is_active=False,
            last_login__lt=cutoff
        ).delete()
        self.stdout.write(f'Deleted {deleted} inactive user(s).')