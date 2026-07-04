from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.tickets.models import Asset, AssetLog

User = get_user_model()

class Command(BaseCommand):
    help = 'Backfill assignment logs for existing assets'

    def handle(self, *args, **options):
        # Get or create a system user for backfilling
        system_user = User.objects.filter(is_superuser=True).first()
        if not system_user:
            self.stdout.write(self.style.ERROR('No superuser found. Please create one first.'))
            return

        updated = 0
        for asset in Asset.objects.all():
            # Check if asset already has assignment logs
            has_assign_logs = asset.logs.filter(action=AssetLog.Action.ASSIGNED).exists()
            
            if not has_assign_logs and asset.assigned_to:
                # Create initial assignment log
                AssetLog.objects.create(
                    asset=asset,
                    action=AssetLog.Action.ASSIGNED,
                    actor=system_user,
                    details={
                        'from': None,
                        'to': asset.assigned_to.get_full_name() if asset.assigned_to else None,
                        'comment': 'Initial assignment (backfilled)'
                    }
                )
                updated += 1
                self.stdout.write(f'✅ Backfilled assignment for {asset.tracking_id}')

        self.stdout.write(self.style.SUCCESS(f'\n🎉 Done! Backfilled {updated} assets.'))