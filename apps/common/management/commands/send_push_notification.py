# apps/common/management/commands/send_push_notifications.py
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.common.models import Notification
from apps.common.utils import send_push_notification

class Command(BaseCommand):
    help = 'Send pending push notifications for unread notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Maximum number of notifications to process',
        )

    def handle(self, *args, **options):
        limit = options['limit']
        # Get unread notifications that haven't been pushed yet
        # We don't have a "pushed" flag, so we'll just send for all unread.
        # To avoid duplicates, we could add a `push_sent_at` field.
        # For now, we'll send for the most recent unread.
        notifications = Notification.objects.filter(is_read=False).order_by('-created_at')[:limit]

        total_sent = 0
        total_failed = 0
        total_expired = 0

        for notification in notifications:
            result = send_push_notification(notification)
            total_sent += result['sent']
            total_failed += result['failed']
            total_expired += result['expired']

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {len(notifications)} notifications: "
                f"{total_sent} sent, {total_failed} failed, {total_expired} expired subscriptions removed."
            )
        )