from django.core.management.base import BaseCommand
from apps.common.models import Category
from django.utils.text import slugify

CATEGORIES = [
    "Software",
    "Hardware",
    "Networking",
    "Repair",
    "Item acquisition",
    "Security",
    "Microsoft apps related",
    "File Server",
    "PMS related",
]

class Command(BaseCommand):
    help = 'Seed the initial ticket categories'

    def handle(self, *args, **options):
        # Check if categories already exist
        if Category.objects.exists():
            self.stdout.write(self.style.WARNING('⚠️ Categories already exist. Skipping seeding to avoid duplicates.'))
            self.stdout.write(self.style.WARNING(f'   Current category count: {Category.objects.count()}'))
            return
        for name in CATEGORIES:
            category, created = Category.objects.get_or_create(
                name=name,
                defaults={'slug': slugify(name)}
            )
            if created:
                self.stdout.write(f'Created category: {name}')
            else:
                self.stdout.write(f'Category already exists: {name}')
        self.stdout.write(self.style.SUCCESS('Categories seeded.'))