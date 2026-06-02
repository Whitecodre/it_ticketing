from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from .models import Ticket, TicketComment, TicketActivityLog
from apps.accounts.models import User
from apps.common.models import Notification

@receiver(post_save, sender=Ticket)
def create_ticket_notification(sender, instance, created, **kwargs):
    if created:
        print("Ticket created signal fired!")   # <-- add this
        # Notify the requester
        Notification.objects.create(
            recipient=instance.requester,
            message=f"Ticket {instance.number} created successfully.",
            url=reverse('tickets:detail', args=[instance.pk])
        )
        # Notify all agents/team leads (unassigned queue alert)
        agents = User.objects.filter(role__in=[User.Role.AGENT, User.Role.TEAM_LEAD])
        for agent in agents:
            Notification.objects.create(
                recipient=agent,
                message=f"New unassigned ticket {instance.number}: {instance.title}",
                url=reverse('tickets:detail', args=[instance.pk])
            )

@receiver(post_save, sender=TicketComment)
def create_comment_notification(sender, instance, created, **kwargs):
    if created and instance.visibility == TicketComment.Visibility.PUBLIC:
        # Notify the requester if someone else replied
        if instance.author != instance.ticket.requester:
            Notification.objects.create(
                recipient=instance.ticket.requester,
                message=f"New reply on ticket {instance.ticket.number}.",
                url=reverse('tickets:detail', args=[instance.ticket.pk])
            )
        # Notify the assigned agent (if any) when the requester posts a reply
        if instance.author == instance.ticket.requester and instance.ticket.assigned_to:
            Notification.objects.create(
                recipient=instance.ticket.assigned_to,
                message=f"{instance.ticket.requester.get_full_name()} replied to ticket {instance.ticket.number}.",
                url=reverse('tickets:detail', args=[instance.ticket.pk])
            )

@receiver(post_save, sender=Ticket)
def log_ticket_changes(sender, instance, created, **kwargs):
    if created:
        TicketActivityLog.objects.create(
            ticket=instance,
            action='created',
            actor=instance.requester,
            details={'status': instance.status, 'priority': instance.get_priority_display()}
        )
    else:
        # Detect status changes using Django's tracker or by comparing with db
        # Simpler: log on every save if status/assignee changed
        if instance.tracker.has_changed('status'):
            TicketActivityLog.objects.create(
                ticket=instance,
                action='status_changed',
                actor=None,  # we'll pass actor from views
                details={'from': instance.tracker.previous('status'), 'to': instance.status}
            )
        if instance.tracker.has_changed('assigned_to_id'):
            old_id = instance.tracker.previous('assigned_to_id')
            new_id = instance.assigned_to_id
            TicketActivityLog.objects.create(
                ticket=instance,
                action='assigned' if new_id else 'unassigned',
                actor=None,
                details={'from': old_id, 'to': new_id}
            )


            