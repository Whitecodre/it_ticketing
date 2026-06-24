from django.core.management.base import BaseCommand
from apps.tickets.models import RemoteConnector

class Command(BaseCommand):
    help = 'Seed default remote connectors'

    def handle(self, *args, **options):
        connector, created = RemoteConnector.objects.get_or_create(
            name='Quick Assist',
            defaults={
                'is_active': True,
                'instructions_for_requester': '1. Open Quick Assist (search in Windows start menu).\n2. Click "Get assistance".\n3. Wait for the agent to provide a 6-digit code.\n4. Enter the code and allow screen sharing.\n5. The session will begin.',
                'instructions_for_agent': '1. Open Quick Assist.\n2. Click "Help someone".\n3. A 6-digit code appears – share it with the user.\n4. The code expires in about 10 minutes.\n5. Once the user enters the code, you will have control.',
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('✅ Quick Assist connector created.'))
        else:
            self.stdout.write('ℹ️ Quick Assist connector already exists.')