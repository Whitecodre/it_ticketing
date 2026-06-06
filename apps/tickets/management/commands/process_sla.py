from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from apps.tickets.models import Ticket, SLA, EscalationRule, TicketActivityLog
from apps.accounts.models import User
from apps.common.models import Notification

class Command(BaseCommand):
    help = 'Process SLA timers and trigger escalation actions'

    def handle(self, *args, **options):
        now = timezone.now()
        active_tickets = Ticket.objects.exclude(
            status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]
        ).filter(
            Q(response_due_at__isnull=False) | Q(resolution_due_at__isnull=False)
        )

        for ticket in active_tickets:
            self.process_timer(ticket, 'response', now)
            self.process_timer(ticket, 'resolution', now)

    def process_timer(self, ticket, timer_type, now):
        due_field = 'response_due_at' if timer_type == 'response' else 'resolution_due_at'
        due_at = getattr(ticket, due_field)
        if not due_at:
            return

        try:
            sla = SLA.objects.get(priority=ticket.priority)
            total_minutes = sla.response_minutes if timer_type == 'response' else sla.resolution_minutes
        except SLA.DoesNotExist:
            return
        if total_minutes == 0:
            return

        elapsed = (now - ticket.created_at).total_seconds() / 60
        percent_elapsed = (elapsed / total_minutes) * 100

        rules = EscalationRule.objects.filter(
            priority=ticket.priority,
            timer_type=timer_type
        ).order_by('threshold_percent')

        for rule in rules:
            if percent_elapsed >= rule.threshold_percent:
                # Check if this escalation already executed
                if TicketActivityLog.objects.filter(
                    ticket=ticket,
                    action='escalation',
                    details__rule_id=rule.pk
                ).exists():
                    continue

                self.execute_escalation(ticket, rule, timer_type, percent_elapsed)

    def execute_escalation(self, ticket, rule, timer_type, percent_elapsed):
        # Log the escalation
        TicketActivityLog.objects.create(
            ticket=ticket,
            action='escalation',
            actor=None,
            details={
                'rule_id': rule.pk,
                'timer_type': timer_type,
                'threshold': rule.threshold_percent,
                'elapsed_pct': round(percent_elapsed, 1),
                'action': rule.action_type,
            }
        )

        if rule.action_type == 'notify' and rule.notify_role:
            recipients = User.objects.filter(role=rule.notify_role, is_active=True)
            for user in recipients:
                Notification.objects.create(
                    recipient=user,
                    message=f'SLA {timer_type} threshold reached for ticket {ticket.number}.',
                    url=f'/tickets/{ticket.pk}/conversation/'
                )

        elif rule.action_type == 'reassign' and rule.reassign_to_role:
            target = User.objects.filter(role=rule.reassign_to_role, is_active=True).first()
            if target and target != ticket.assigned_to:
                old = ticket.assigned_to
                ticket.assigned_to = target
                ticket.save(update_fields=['assigned_to'])
                TicketActivityLog.objects.create(
                    ticket=ticket,
                    action='assigned',
                    actor=None,
                    details={'from': old.get_full_name() if old else 'Unassigned',
                             'to': target.get_full_name(),
                             'reason': f'SLA {timer_type} escalation'}
                )
                Notification.objects.create(
                    recipient=target,
                    message=f'You have been assigned ticket {ticket.number} due to SLA escalation.',
                    url=f'/tickets/{ticket.pk}/conversation/'
                )

        # add_watcher can be added later