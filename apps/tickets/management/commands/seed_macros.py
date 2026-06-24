from django.core.management.base import BaseCommand
from apps.tickets.models import Macro
from apps.accounts.models import User

class Command(BaseCommand):
    help = 'Seed default macros'

    def handle(self, *args, **options):
        creator = User.objects.filter(is_superuser=True).first()
        if not creator:
            self.stdout.write(self.style.ERROR('No superuser found. Please create one first.'))
            return

        macros = [
            {
                'title': 'Thank you for contacting us',
                'body': 'Thank you for reaching out. We have received your request and will get back to you as soon as possible.',
                'visibility': 'PUBLIC'
            },
            {
                'title': 'Please provide more details',
                'body': 'Could you please provide more details about the issue? It will help us understand and resolve it faster.',
                'visibility': 'PUBLIC'
            },
            {
                'title': 'We are working on it',
                'body': 'We are currently investigating this issue. We will update you as soon as we have more information.',
                'visibility': 'PUBLIC'
            },
            {
                'title': 'Resolution confirmation',
                'body': 'We believe this issue has been resolved. Could you please confirm that everything is working as expected?',
                'visibility': 'PUBLIC'
            },
            {
                'title': 'Escalation to internal team',
                'body': 'We have escalated this issue to our internal team for further investigation. We will keep you updated.',
                'visibility': 'INTERNAL'
            },
            {
                'title': 'Request for remote session',
                'body': 'We would like to schedule a remote session to assist you further. Please let us know a convenient time.',
                'visibility': 'PUBLIC'
            },
            {
                'title': 'Known issue – workaround',
                'body': 'This is a known issue. We recommend the following workaround: [describe workaround]. We are working on a permanent fix.',
                'visibility': 'PUBLIC'
            },
            {
                'title': 'Ticket closed – no response',
                'body': 'We have not received a response from you. We are closing this ticket. If you still need assistance, please reopen it.',
                'visibility': 'PUBLIC'
            },
        ]


        for macro_data in macros:
            obj, created = Macro.objects.get_or_create(
                title=macro_data['title'],
                defaults={
                    'body': macro_data['body'],
                    'visibility': macro_data['visibility'],
                    'created_by': creator,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✅ Created macro: {obj.title}'))
            else:
                self.stdout.write(f'ℹ️ Macro already exists: {obj.title}')