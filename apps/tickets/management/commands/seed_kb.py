from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from apps.knowledge_base.models import Article
from apps.common.models import Category

# slug = slugify(data['title'])

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed sample knowledge base articles'

    def handle(self, *args, **options):
        # Get or create categories
        categories = {}
        cat_names = ['IT', 'HR', 'Operations', 'General', 'Security']
        for name in cat_names:
            cat, _ = Category.objects.get_or_create(
                name=name,
                defaults={'slug': slugify(name)}
            )
            categories[name] = cat
            self.stdout.write(f'✅ Category: {name}')

        # Get a superuser as author
        author = User.objects.filter(is_superuser=True).first()
        if not author:
            self.stdout.write(self.style.ERROR('No superuser found. Please create one first.'))
            return

        articles_data = [
            {
                'title': 'How to reset your multi‑factor authentication',
                'category': 'IT',
                'content': 'To reset your MFA, please contact the IT helpdesk. You will need to verify your identity before a new token can be issued.',
                'visibility': 'PUBLIC',
                'status': 'PUBLISHED',
            },
            {
                'title': 'Connecting to corporate WiFi on personal devices',
                'category': 'IT',
                'content': 'Follow these steps to connect: 1. Select the "CorpWiFi" network. 2. Enter your corporate email and password. 3. Accept the certificate.',
                'visibility': 'PUBLIC',
                'status': 'PUBLISHED',
            },
            {
                'title': 'Printers offline on 4th floor – troubleshooting',
                'category': 'IT',
                'content': 'If printers on the 4th floor are offline, try restarting the print spooler service. If that fails, contact the IT support team.',
                'visibility': 'PUBLIC',
                'status': 'PUBLISHED',
            },
            {
                'title': 'New starter hardware request process',
                'category': 'Operations',
                'content': 'To request hardware for a new starter, fill out the New Starter Hardware Request form in the Service Catalogue. Provide the start date and role.',
                'visibility': 'PUBLIC',
                'status': 'PUBLISHED',
            },
            {
                'title': 'How to reset your Windows password',
                'category': 'IT',
                'content': 'You can reset your Windows password using the self‑service portal: https://passwordreset.example.com. You will need to verify your identity.',
                'visibility': 'PUBLIC',
                'status': 'PUBLISHED',
            },
            {
                'title': 'Email sync error on mobile devices',
                'category': 'IT',
                'content': 'If your emails are not syncing on your mobile device, try removing and re‑adding your account. Ensure your device is running the latest OS version.',
                'visibility': 'PUBLIC',
                'status': 'PUBLISHED',
            },
            {
                'title': 'Software license renewal: Adobe Suite',
                'category': 'IT',
                'content': 'Adobe Suite licenses are renewed annually. A reminder will be sent to the department head before the renewal date. Please confirm the number of licenses needed.',
                'visibility': 'PUBLIC',
                'status': 'PUBLISHED',
            },
            {
                'title': 'VPN connectivity issues in London office',
                'category': 'IT',
                'content': 'If you are experiencing VPN issues in the London office, please ensure you are using the latest VPN client. Also check your network connection.',
                'visibility': 'PUBLIC',
                'status': 'PUBLISHED',
            },
            {
                'title': 'Employee offboarding checklist',
                'category': 'HR',
                'content': 'When an employee leaves, follow the offboarding checklist: 1. Disable access 2. Collect equipment 3. Remove from groups 4. Archive email.',
                'visibility': 'INTERNAL',
                'status': 'PUBLISHED',
            },
            {
                'title': 'Draft: New remote work policy',
                'category': 'HR',
                'content': 'This is a draft policy for remote work. It will be reviewed by the leadership team before publication.',
                'visibility': 'INTERNAL',
                'status': 'DRAFT',
            },
            {
                'title': 'Pending review: Security incident reporting procedure',
                'category': 'Security',
                'content': 'This article describes the procedure for reporting security incidents. It is pending review by the security team.',
                'visibility': 'INTERNAL',
                'status': 'PENDING_REVIEW',
            },
        ]

        created_count = 0
        for data in articles_data:
            slug = slugify(data['title'])
            article, created = Article.objects.get_or_create(
                slug=slug,
                defaults={
                    'title': data['title'],
                    'category': categories.get(data['category']),
                    'author': author,
                    'content': data['content'],
                    'visibility': data['visibility'],
                    'status': data['status'],
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✅ Created article: {article.title}'))
            else:
                self.stdout.write(f'ℹ️ Article already exists: {article.title}')

        self.stdout.write(self.style.SUCCESS(f'\n🎉 Done! {created_count} new articles created.'))