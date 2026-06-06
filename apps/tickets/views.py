import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.management import call_command
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Avg, Q, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
from .forms import TicketForm, CommentForm
from .models import Ticket, TicketComment, Macro, TicketActivityLog, SLA, EscalationRule, BusinessCalendar
from apps.accounts.models import User
from apps.common.models import Notification

# ---------- Helper ----------
def get_sidebar_template(user):
    """Return the correct sidebar partial for the user's role."""
    mapping = {
        'END_USER': 'partials/sidebar_end_user.html',
        'AGENT': 'partials/sidebar_agent.html',
        'TEAM_LEAD': 'partials/sidebar_team_lead.html',
        'ADMIN': 'partials/sidebar_admin.html',
        'SUPERADMIN': 'partials/sidebar_superadmin.html',
        'APPROVER': 'partials/sidebar_approver.html',
    }
    return mapping.get(user.role, 'partials/sidebar_end_user.html')

# ---------- Ticket Creation ----------
@login_required
def create_ticket(request):
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.requester = request.user

            # Determine number prefix based on ticket type
            prefix = 'TK' if ticket.type == Ticket.Type.INCIDENT else 'SRV'

            # Generate a unique 4-digit suffix
            for _ in range(20):
                suffix = str(random.randint(0, 9999)).zfill(4)
                candidate = f"{prefix}#{suffix}"
                if not Ticket.objects.filter(number=candidate).exists():
                    ticket.number = candidate
                    break
            else:
                import time
                ticket.number = f"{prefix}#{int(time.time()) % 10000:04d}"

            ticket.save()

            def apply_sla(ticket):
                try:
                    sla = SLA.objects.get(priority=ticket.priority)
                except SLA.DoesNotExist:
                    return
                now = timezone.now()
                ticket.response_due_at = now + timedelta(minutes=sla.response_minutes)
                ticket.resolution_due_at = now + timedelta(minutes=sla.resolution_minutes)
                ticket.save(update_fields=['response_due_at', 'resolution_due_at'])

            if ticket.type == Ticket.Type.SERVICE_REQUEST:
                ticket.status = Ticket.Status.PENDING_APPROVAL
                ticket.save(update_fields=['status'])
            apply_sla(ticket)
            return redirect('tickets:detail', pk=ticket.pk)
    else:
        form = TicketForm()
    return render(request, 'requester/ticket_form.html', {'form': form})

# ---------- Cancel Ticket ----------
@login_required
@require_POST
def cancel_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.user != ticket.requester:
        return HttpResponse(status=403)
    if ticket.status not in [Ticket.Status.NEW, Ticket.Status.TRIAGED]:
        return HttpResponse(status=400)
    ticket.status = Ticket.Status.CLOSED
    ticket.save()
    TicketActivityLog.objects.create(
        ticket=ticket, action='status_changed', actor=request.user,
        details={'from': ticket.status, 'to': Ticket.Status.CLOSED, 'reason': 'Cancelled by requester'}
    )
    if request.headers.get('HX-Request'):
        tickets = Ticket.objects.filter(requester=request.user).order_by('-created_at')
        status_filter = request.POST.get('current_status', '')
        if status_filter:
            tickets = tickets.filter(status=status_filter)
        return render(request, 'partials/ticket_table.html', {'tickets': tickets, 'current_status': status_filter})
    return redirect('tickets:my_list')

# ---------- My Tickets List ----------
@login_required
def my_ticket_list(request):
    tickets = Ticket.objects.filter(requester=request.user).order_by('-created_at')
    status_filter = request.GET.get('status')
    if status_filter and status_filter.upper() in dict(Ticket.Status.choices):
        tickets = tickets.filter(status=status_filter.upper())

    paginator = Paginator(tickets, 10)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    context = {
        'tickets': page_obj,
        'current_status': status_filter or '',
        'status_choices': Ticket.Status.choices,
        'sidebar_template': get_sidebar_template(request.user),
    }

    if request.headers.get('HX-Request'):
        return render(request, 'partials/ticket_list_partial.html', context)
    return render(request, 'requester/ticket_list.html', context)

# ---------- Ticket Detail (Requester) ----------
@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.user != ticket.requester and request.user.role not in ['AGENT', 'TEAM_LEAD', 'ADMIN', 'SUPERADMIN']:
        return redirect('dashboard')

    comments = ticket.comments.filter(visibility=TicketComment.Visibility.PUBLIC).order_by('created_at')
    form = CommentForm()

    if request.method == 'POST' and request.headers.get('HX-Request'):
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.ticket = ticket
            comment.author = request.user
            comment.visibility = TicketComment.Visibility.PUBLIC
            comment.save()

            if ticket.status == Ticket.Status.PENDING_USER:
                ticket.status = Ticket.Status.IN_PROGRESS
                ticket.save()
            TicketActivityLog.objects.create(
                ticket=ticket, action='status_changed', actor=request.user,
                details={'from': Ticket.Status.PENDING_USER, 'to': Ticket.Status.IN_PROGRESS}
            )
            comments = ticket.comments.filter(visibility=TicketComment.Visibility.PUBLIC).order_by('created_at')
            return render(request, 'partials/comment_thread.html', {'ticket': ticket, 'comments': comments})
        else:
            return render(request, 'partials/comment_form.html', {'form': form, 'ticket': ticket}, status=422)

    return render(request, 'requester/ticket_detail.html', {
        'ticket': ticket,
        'comments': comments,
        'form': form,
        'sidebar_template': get_sidebar_template(request.user),
    })

# ---------- Unassigned Queue ----------
@login_required
def unassigned_queue(request):
    tickets = Ticket.objects.filter(
        assigned_to__isnull=True
    ).exclude(
        status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED, Ticket.Status.PENDING_APPROVAL]
    ).order_by('-created_at')

    assignable_agents = User.objects.filter(role__in=['AGENT', 'TEAM_LEAD']).only('pk', 'first_name', 'last_name', 'email')

    context = {
        'tickets': tickets,
        'assignable_agents': assignable_agents,
        'status_choices': Ticket.Status.choices,
        'sidebar_template': get_sidebar_template(request.user),
    }
    return render(request, 'agent/unassigned_queue.html', context)

# ---------- Assigned to Me ----------
@login_required
def assigned_to_me(request):
    tickets = Ticket.objects.filter(
        assigned_to=request.user
    ).exclude(
        status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED, Ticket.Status.PENDING_APPROVAL]
    ).order_by('-created_at')

    assignable_agents = User.objects.filter(role__in=['AGENT', 'TEAM_LEAD']).only('pk', 'first_name', 'last_name', 'email')

    context = {
        'tickets': tickets,
        'assignable_agents': assignable_agents,
        'status_choices': Ticket.Status.choices,
        'sidebar_template': get_sidebar_template(request.user),
    }
    return render(request, 'agent/assigned_to_me.html', context)

# ---------- Claim Ticket ----------
@login_required
def claim_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if ticket.assigned_to is None:
        ticket.assigned_to = request.user
        ticket.status = Ticket.Status.ASSIGNED
        ticket.save()
        TicketActivityLog.objects.create(
            ticket=ticket, action='assigned', actor=request.user,
            details={'to': request.user.get_full_name(), 'status': ticket.status}
        )
    tickets = Ticket.objects.filter(assigned_to__isnull=True).exclude(
        status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED, Ticket.Status.PENDING_APPROVAL]
    ).order_by('-created_at')
    return render(request, 'partials/agent_ticket_table.html', {'tickets': tickets})

# ---------- Agent Ticket Detail (Slide‑over) ----------
@login_required
def agent_ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.user.role not in [User.Role.AGENT, User.Role.TEAM_LEAD, User.Role.ADMIN, User.Role.SUPERADMIN]:
        return HttpResponse(status=403)
    comments = ticket.comments.all().order_by('created_at')
    return render(request, 'partials/ticket_slideover.html', {
        'ticket': ticket,
        'comments': comments,
    })

# ---------- Agent Conversation Page ----------
@login_required
def agent_ticket_conversation(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.user.role not in [User.Role.AGENT, User.Role.TEAM_LEAD, User.Role.ADMIN, User.Role.SUPERADMIN]:
        return HttpResponse(status=403)

    comments = ticket.comments.all().order_by('created_at')
    form = CommentForm()
    return render(request, 'agent/ticket_conversation.html', {
        'ticket': ticket,
        'comments': comments,
        'form': form,
        'sidebar_template': get_sidebar_template(request.user),
    })

# ---------- Add Comment (Conversation) ----------
@login_required
@require_POST
def add_comment_conversation(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.ticket = ticket
        comment.author = request.user
        comment.visibility = request.POST.get('visibility', 'PUBLIC').upper()
        if comment.visibility not in ['PUBLIC', 'INTERNAL']:
            comment.visibility = 'PUBLIC'
        comment.save()

        TicketActivityLog.objects.create(
            ticket=ticket, action='commented', actor=request.user,
            details={'visibility': comment.visibility, 'body': comment.body[:200]}
        )

        old_status = ticket.status
        if comment.visibility == 'PUBLIC':
            if old_status in [Ticket.Status.ASSIGNED, Ticket.Status.IN_PROGRESS,
                              Ticket.Status.PENDING_USER, Ticket.Status.NEW, Ticket.Status.TRIAGED]:
                ticket.status = Ticket.Status.IN_PROGRESS
                ticket.save()
                if old_status != ticket.status:
                    TicketActivityLog.objects.create(
                        ticket=ticket, action='status_changed', actor=request.user,
                        details={'from': old_status, 'to': ticket.status}
                    )

    comments = ticket.comments.all().order_by('created_at')
    return render(request, 'partials/conversation_timeline.html', {
        'ticket': ticket,
        'comments': comments,
    })

# ---------- Update Ticket Status ----------
@login_required
@require_POST
def update_status(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    previous_status = ticket.status
    new_status = request.GET.get('status')
    if new_status and new_status in dict(Ticket.Status.choices):
        ticket.status = new_status
        ticket.save()
        TicketActivityLog.objects.create(
            ticket=ticket, action='status_changed', actor=request.user,
            details={'from': previous_status, 'to': new_status}
        )
    return HttpResponse(status=204)

# ---------- Ticket Details Panel ----------
@login_required
def ticket_details_panel(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    followers = User.objects.filter(role__in=['AGENT','TEAM_LEAD'])[:5]
    return render(request, 'partials/ticket_details_panel.html', {
        'ticket': ticket,
        'followers': followers,
    })

# ---------- Edit Subject ----------
@login_required
@require_POST
def edit_subject(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    new_title = request.POST.get('title', '').strip()
    if new_title:
        ticket.title = new_title
        ticket.save()
    return render(request, 'partials/subject_display.html', {'ticket': ticket})

# ---------- Assign Popover ----------
@login_required
def assign_popover(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    agents = User.objects.filter(role__in=['AGENT', 'TEAM_LEAD'])[:10]
    return render(request, 'partials/popovers/assign_popover.html', {'ticket': ticket, 'agents': agents})

# ---------- Assign to Me ----------
@login_required
@require_POST
def assign_to_me(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    ticket.assigned_to = request.user
    ticket.save()
    return render(request, 'partials/ticket_details_assignee.html', {'ticket': ticket})

# ---------- Assign Specific ----------
@login_required
@require_POST
def assign_specific(request, pk, user_pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    agent = get_object_or_404(User, pk=user_pk)
    ticket.assigned_to = agent
    ticket.save()
    return render(request, 'partials/ticket_details_assignee.html', {'ticket': ticket})

# ---------- Followers (stubs) ----------
@login_required
@require_POST
def remove_follower(request, ticket_pk, user_pk):
    return HttpResponse(status=204)

@login_required
def add_follower_popover(request, ticket_pk):
    return render(request, 'partials/popovers/add_follower_popover.html', {
        'ticket': get_object_or_404(Ticket, pk=ticket_pk),
        'agents': User.objects.filter(role__in=['AGENT','TEAM_LEAD'])[:10],
    })

# ---------- Popover stubs ----------
def edit_group_popover(request, pk):
    return render(request, 'partials/popovers/empty.html')
def edit_type_popover(request, pk):
    return render(request, 'partials/popovers/empty.html')
def edit_priority_popover(request, pk):
    return render(request, 'partials/popovers/empty.html')
def add_tag_popover(request, pk):
    return render(request, 'partials/popovers/empty.html')
def remove_tag(request, pk, tag_pk):
    return HttpResponse(status=204)

# ---------- Macros ----------
@login_required
def macro_list(request):
    macros = Macro.objects.all()
    return render(request, 'partials/macro_dropdown.html', {'macros': macros})

# ---------- Bulk Action ----------
@login_required
@require_POST
def bulk_action(request):
    ticket_ids_str = request.POST.get('ticket_ids', '')
    action = request.POST.get('action', '')
    value = request.POST.get('value', '')
    if not ticket_ids_str or not action:
        return HttpResponse(status=400)

    ids = [int(pk) for pk in ticket_ids_str.split(',') if pk.strip().isdigit()]
    tickets = Ticket.objects.filter(pk__in=ids)

    if action == 'status':
        if value in dict(Ticket.Status.choices):
            for ticket in tickets:
                old_status = ticket.status
                ticket.status = value
                ticket.save()
                TicketActivityLog.objects.create(
                    ticket=ticket, action='status_changed', actor=request.user,
                    details={'from': old_status, 'to': value, 'method': 'bulk'}
                )
    elif action == 'assign':
        if request.user.role not in ['TEAM_LEAD', 'ADMIN', 'SUPERADMIN']:
            return HttpResponse(status=403)
        if value.isdigit():
            agent = get_object_or_404(User, pk=int(value))
            for ticket in tickets:
                old_assignee = ticket.assigned_to
                ticket.assigned_to = agent
                ticket.save()
                TicketActivityLog.objects.create(
                    ticket=ticket, action='assigned', actor=request.user,
                    details={'from': old_assignee.get_full_name() if old_assignee else 'Unassigned',
                             'to': agent.get_full_name(), 'method': 'bulk'}
                )

    source = request.POST.get('source', 'unassigned')
    if source == 'assigned':
        tickets = Ticket.objects.filter(
            assigned_to=request.user
        ).exclude(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED, Ticket.Status.PENDING_APPROVAL]
        ).order_by('-created_at')
    else:
        tickets = Ticket.objects.filter(
            assigned_to__isnull=True
        ).exclude(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]
        ).order_by('-created_at')

    assignable_agents = User.objects.filter(role__in=['AGENT', 'TEAM_LEAD']).only('pk', 'first_name', 'last_name', 'email')
    return render(request, 'partials/agent_ticket_table.html', {
        'tickets': tickets,
        'assignable_agents': assignable_agents,
        'status_choices': Ticket.Status.choices,
    })

# ---------- Team Queue ----------
@login_required
def team_queue(request):
    if request.user.role != 'TEAM_LEAD':
        return HttpResponse(status=403)
    team_members = User.objects.filter(department=request.user.department, role='AGENT')
    tickets = Ticket.objects.filter(
        assigned_to__in=team_members
    ).exclude(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]
    ).order_by('-created_at')

    agent_id = request.GET.get('agent')
    if agent_id:
        tickets = tickets.filter(assigned_to_id=agent_id)

    context = {
        'tickets': tickets,
        'team_members': team_members,
        'selected_agent': agent_id,
        'sidebar_template': get_sidebar_template(request.user),
    }
    return render(request, 'partials/team_queue.html', context)

# ---------- Team Reassign ----------
@login_required
@require_POST
def team_reassign(request, pk):
    if request.user.role != 'TEAM_LEAD':
        return HttpResponse(status=403)
    ticket = get_object_or_404(Ticket, pk=pk)
    new_agent_id = request.POST.get('agent_id')
    agent = get_object_or_404(User, pk=new_agent_id, role='AGENT')
    old_assignee = ticket.assigned_to
    ticket.assigned_to = agent
    ticket.save()
    TicketActivityLog.objects.create(
        ticket=ticket, action='assigned', actor=request.user,
        details={'from': old_assignee.get_full_name() if old_assignee else 'Unassigned',
                 'to': agent.get_full_name()}
    )
    return JsonResponse({'status': 'ok'})

# ---------- Audit Log ----------
@login_required
def audit_log(request):
    if request.user.role not in ['TEAM_LEAD', 'ADMIN', 'SUPERADMIN']:
        return HttpResponse(status=403)

    logs = TicketActivityLog.objects.select_related('ticket', 'actor').all()
    if request.user.role == 'TEAM_LEAD':
        team_members = User.objects.filter(department=request.user.department, role='AGENT')
        logs = logs.filter(
            Q(ticket__assigned_to__in=team_members) | Q(ticket__requester__in=team_members)
        )

    action = request.GET.get('action')
    ticket_id = request.GET.get('ticket')
    if action:
        logs = logs.filter(action=action)
    if ticket_id:
        logs = logs.filter(ticket__number__icontains=ticket_id)
    logs = logs.order_by('-created_at')[:100]

    context = {
        'logs': logs,
        'action_choices': ['created', 'status_changed', 'assigned', 'unassigned', 'commented'],
        'sidebar_template': get_sidebar_template(request.user),
    }
    return render(request, 'partials/audit_log.html', context)

# ---------- Reports Dashboard ----------
@login_required
def reports_dashboard(request):
    user = request.user
    if user.role not in ['ADMIN', 'SUPERADMIN', 'TEAM_LEAD']:
        return HttpResponse(status=403)

    if user.role == 'TEAM_LEAD':
        team_members = User.objects.filter(department=user.department, role='AGENT')
        ticket_filter = Q(assigned_to__in=team_members) | Q(requester__in=team_members)
    else:
        ticket_filter = Q()

    slas = SLA.objects.all().order_by('priority')
    sla_data = []
    for sla in slas:
        resolved = Ticket.objects.filter(
            ticket_filter, priority=sla.priority,
            status__in=['RESOLVED', 'CLOSED'], resolved_at__isnull=False
        )
        total = resolved.count()
        if total == 0:
            compliance = 100
        else:
            compliant = sum(
                1 for t in resolved
                if t.resolved_at and (t.resolved_at - t.created_at).total_seconds() / 60 <= sla.resolution_minutes
            )
            compliance = round((compliant / total) * 100, 1)
        sla_data.append({'priority': sla.get_priority_display(), 'compliance': compliance})

    end = timezone.now().date()
    start = end - timedelta(days=29)
    created_qs = Ticket.objects.filter(
        ticket_filter, created_at__date__gte=start
    ).annotate(date=TruncDate('created_at')).values('date').annotate(count=Count('id')).order_by('date')
    resolved_qs = Ticket.objects.filter(
        ticket_filter, resolved_at__isnull=False, resolved_at__date__gte=start
    ).annotate(date=TruncDate('resolved_at')).values('date').annotate(count=Count('id')).order_by('date')

    dates, created_counts, resolved_counts = [], [], []
    for i in range(30):
        d = start + timedelta(days=i)
        dates.append(d.strftime('%m/%d'))
        created_counts.append(next((x['count'] for x in created_qs if x['date'] == d), 0))
        resolved_counts.append(next((x['count'] for x in resolved_qs if x['date'] == d), 0))

    resolved = Ticket.objects.filter(
        ticket_filter, status__in=['RESOLVED', 'CLOSED'], resolved_at__isnull=False
    )
    mttr = resolved.aggregate(avg_mttr=Avg(F('resolved_at') - F('created_at')))['avg_mttr']
    mttr_minutes = round(mttr.total_seconds() / 60) if mttr else 0

    backlog = Ticket.objects.filter(
        ticket_filter,
        status__in=['NEW', 'TRIAGED', 'ASSIGNED', 'IN_PROGRESS', 'PENDING_USER', 'PENDING_VENDOR'],
        created_at__lt=timezone.now() - timedelta(days=7)
    ).count()

    open_by_priority = Ticket.objects.filter(
        ticket_filter,
        status__in=['NEW', 'TRIAGED', 'ASSIGNED', 'IN_PROGRESS', 'PENDING_USER', 'PENDING_VENDOR']
    ).values('priority').annotate(count=Count('id')).order_by('priority')

    open_labels, open_data = [], []
    for p in open_by_priority:
        open_labels.append(dict(Ticket.Priority.choices)[p['priority']])
        open_data.append(p['count'])

    context = {
        'sla_data': sla_data,
        'volume_dates': dates,
        'volume_created': created_counts,
        'volume_resolved': resolved_counts,
        'mttr_minutes': mttr_minutes,
        'backlog': backlog,
        'open_priority_labels': open_labels,
        'open_priority_data': open_data,
        'open_total': sum(open_data),
        'sidebar_template': get_sidebar_template(request.user),
    }
    return render(request, 'dashboards/reports.html', context)

# ---------- SLA Trigger (external cron) ----------
@csrf_exempt
def trigger_sla_processing(request):
    secret = request.GET.get('secret')
    if secret != 'jkeihwihivkgyg678448bhct36gysyvy!!gygrv':
        return HttpResponse(status=403)
    try:
        call_command('process_sla')
        return HttpResponse('SLA processed OK', status=200)
    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=500)

# ---------- Placeholder / Static Pages ----------
@login_required
def catalogue(request):
    if request.user.role not in ['ADMIN', 'SUPERADMIN']:
        return HttpResponse(status=403)
    return render(request, 'admin/catalogue.html', {'sidebar_template': get_sidebar_template(request.user)})

@login_required
def connectors(request):
    if request.user.role not in ['ADMIN', 'SUPERADMIN']:
        return HttpResponse(status=403)
    return render(request, 'admin/connectors.html', {'sidebar_template': get_sidebar_template(request.user)})

@login_required
def assets(request):
    return render(request, 'placeholders/coming_soon.html', {'title': 'Assets', 'sidebar_template': get_sidebar_template(request.user)})

@login_required
def remote_sessions(request):
    return render(request, 'placeholders/coming_soon.html', {'title': 'Remote Sessions', 'sidebar_template': get_sidebar_template(request.user)})

def kb_suggestions(request):
    return render(request, 'partials/kb_suggestions.html', {'articles': []})

# ---------- Approver Views ----------
@login_required
def approver_dashboard(request):
    if request.user.role != User.Role.APPROVER:
        return HttpResponse(status=403)
    pending = Ticket.objects.filter(status=Ticket.Status.PENDING_APPROVAL)
    overdue = pending.filter(created_at__lt=timezone.now() - timedelta(days=2))
    recent_logs = TicketActivityLog.objects.filter(
        actor=request.user, action__in=['approved', 'rejected']
    ).select_related('ticket').order_by('-created_at')[:5]
    context = {
        'pending_count': pending.count(),
        'overdue_count': overdue.count(),
        'pending_tickets': pending.order_by('-created_at')[:10],
        'recent_logs': recent_logs,
        'sidebar_template': get_sidebar_template(request.user),
    }
    return render(request, 'dashboards/approver_dashboard.html', context)

@login_required
def approver_pending(request):
    if request.user.role != User.Role.APPROVER:
        return HttpResponse(status=403)
    tickets = Ticket.objects.filter(status=Ticket.Status.PENDING_APPROVAL).order_by('-created_at')
    return render(request, 'partials/approver_pending.html', {'tickets': tickets, 'sidebar_template': get_sidebar_template(request.user)})

@login_required
def approver_history(request):
    if request.user.role != User.Role.APPROVER:
        return HttpResponse(status=403)
    logs = TicketActivityLog.objects.filter(
        actor=request.user, action__in=['approved', 'rejected']
    ).select_related('ticket').order_by('-created_at')[:50]
    return render(request, 'partials/approver_history.html', {'logs': logs, 'sidebar_template': get_sidebar_template(request.user)})

@login_required
@require_POST
def approve_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, status=Ticket.Status.PENDING_APPROVAL)
    if request.user.role != User.Role.APPROVER:
        return HttpResponse(status=403)
    comment = request.POST.get('comment', '')
    ticket.status = Ticket.Status.APPROVED
    ticket.save()
    TicketActivityLog.objects.create(ticket=ticket, action='approved', actor=request.user, details={'comment': comment})
    Notification.objects.create(
        recipient=ticket.requester,
        message=f'Your service request {ticket.number} has been approved.',
        url=reverse('tickets:detail', args=[ticket.pk])
    )
    return redirect('tickets:approver_pending')

@login_required
@require_POST
def reject_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, status=Ticket.Status.PENDING_APPROVAL)
    if request.user.role != User.Role.APPROVER:
        return HttpResponse(status=403)
    comment = request.POST.get('comment', '')
    ticket.status = Ticket.Status.CLOSED
    ticket.save()
    TicketActivityLog.objects.create(ticket=ticket, action='rejected', actor=request.user, details={'comment': comment})
    Notification.objects.create(
        recipient=ticket.requester,
        message=f'Your service request {ticket.number} was rejected. Reason: {comment}',
        url=reverse('tickets:detail', args=[ticket.pk])
    )
    return redirect('tickets:approver_pending')

# ---------- SLA Management (Admin & Superadmin) ----------
def is_admin(user):
    return user.role in ['ADMIN', 'SUPERADMIN']

@login_required
@user_passes_test(is_admin)
def sla_list(request):
    slas = SLA.objects.all().order_by('priority')
    calendars = BusinessCalendar.objects.all()
    rules = EscalationRule.objects.all().order_by('priority', 'timer_type', 'threshold_percent')
    context = {
        'slas': slas,
        'calendars': calendars,
        'rules': rules,
        'priority_choices': Ticket.Priority.choices,
        'sidebar_template': get_sidebar_template(request.user),
    }
    return render(request, 'admin/sla_management.html', context)

@login_required
@user_passes_test(is_admin)
@require_POST
def sla_create(request):
    priority = request.POST.get('priority')
    response = request.POST.get('response_minutes')
    resolution = request.POST.get('resolution_minutes')
    calendar_id = request.POST.get('calendar_id') or None
    SLA.objects.update_or_create(
        priority=priority,
        defaults={'response_minutes': response, 'resolution_minutes': resolution, 'calendar_id': calendar_id}
    )
    return redirect('tickets:sla_management')

@login_required
@user_passes_test(is_admin)
@require_POST
def sla_delete(request, pk):
    sla = get_object_or_404(SLA, pk=pk)
    sla.delete()
    return redirect('tickets:sla_management')

@login_required
def sla_badge(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    return render(request, 'partials/sla_badge.html', {'ticket': ticket})

@login_required
@user_passes_test(is_admin)
@require_POST
def calendar_create(request):
    name = request.POST.get('name')
    workdays = request.POST.getlist('workdays')
    work_start = request.POST.get('work_start')
    work_end = request.POST.get('work_end')
    holidays_str = request.POST.get('holidays', '')
    holidays = [h.strip() for h in holidays_str.split(',') if h.strip()]
    BusinessCalendar.objects.create(
        name=name, workdays=workdays, work_start=work_start, work_end=work_end, holidays=holidays
    )
    return redirect('tickets:sla_management')

@login_required
@user_passes_test(is_admin)
@require_POST
def rule_create(request):
    priority = request.POST.get('priority')
    timer_type = request.POST.get('timer_type')
    threshold = request.POST.get('threshold_percent')
    action = request.POST.get('action_type')
    notify_role = request.POST.get('notify_role') if action == 'notify' else None
    reassign_to_role = request.POST.get('reassign_to_role') if action == 'reassign' else None
    EscalationRule.objects.create(
        priority=priority, timer_type=timer_type, threshold_percent=threshold,
        action_type=action, notify_role=notify_role, reassign_to_role=reassign_to_role
    )
    return redirect('tickets:sla_management')

@login_required
@user_passes_test(is_admin)
@require_POST
def rule_delete(request, pk):
    rule = get_object_or_404(EscalationRule, pk=pk)
    rule.delete()
    return redirect('tickets:sla_management')

@login_required
@user_passes_test(is_admin)
@require_POST
def calendar_delete(request, pk):
    cal = get_object_or_404(BusinessCalendar, pk=pk)
    cal.delete()
    return redirect('tickets:sla_management')