import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from .forms import TicketForm, CommentForm
from .models import Ticket, TicketComment, Macro, TicketActivityLog
from apps.accounts.models import User

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
            for _ in range(20):  # try up to 20 times to avoid infinite loop
                suffix = str(random.randint(0, 9999)).zfill(4)
                candidate = f"{prefix}#{suffix}"
                if not Ticket.objects.filter(number=candidate).exists():
                    ticket.number = candidate
                    break
            else:
                # Fallback: use a timestamp-based suffix if all random attempts collide
                import time
                ticket.number = f"{prefix}#{int(time.time()) % 10000:04d}"

            ticket.save()
            return redirect('tickets:detail', pk=ticket.pk)
    else:
        form = TicketForm()
    return render(request, 'requester/ticket_form.html', {'form': form})

@login_required
def my_ticket_list(request):
    tickets = Ticket.objects.filter(requester=request.user).order_by('-created_at')

    # Optional filtering via query params (used by HTMX filter buttons)
    status_filter = request.GET.get('status')
    if status_filter and status_filter.upper() in dict(Ticket.Status.choices):
        tickets = tickets.filter(status=status_filter.upper())

    # Pagination – 10 tickets per page
    paginator = Paginator(tickets, 10)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    context = {
        'tickets': page_obj,
        'current_status': status_filter or '',
    }
    context['status_choices'] = Ticket.Status.choices

    # If HTMX request, return only the table partial (for filter/pagination)
    if request.headers.get('HX-Request'):
        return render(request, 'partials/ticket_table.html', context)
    return render(request, 'requester/ticket_list.html', context)

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

            # --- AUTOMATION ---
            # If requester replies and the ticket is PENDING_USER, move back to IN_PROGRESS
            if ticket.status == Ticket.Status.PENDING_USER:
                ticket.status = Ticket.Status.IN_PROGRESS
                ticket.save()
            TicketActivityLog.objects.create(
                ticket=ticket,
                action='status_changed',
                actor=request.user,
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
    })

@login_required
def unassigned_queue(request):
    # Tickets with no assignee and still open (not RESOLVED/CLOSED)
    tickets = Ticket.objects.filter(
        assigned_to__isnull=True
    ).exclude(
        status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]
    ).order_by('-created_at')

    assignable_agents = User.objects.filter(role__in=['AGENT', 'TEAM_LEAD']).only('pk', 'first_name', 'last_name', 'email')

    context = {
        'tickets': tickets,
        'assignable_agents': assignable_agents,
        'status_choices': Ticket.Status.choices,
    }
    return render(request, 'agent/unassigned_queue.html', context)


@login_required
def assigned_to_me(request):
    tickets = Ticket.objects.filter(
        assigned_to=request.user
    ).exclude(
        status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]
    ).order_by('-created_at')

    assignable_agents = User.objects.filter(role__in=['AGENT', 'TEAM_LEAD']).only('pk', 'first_name', 'last_name', 'email')

    context = {
        'tickets': tickets,
        'assignable_agents': assignable_agents,
        'status_choices': Ticket.Status.choices,
    }
    return render(request, 'agent/assigned_to_me.html', context)

@login_required
def claim_ticket(request, pk):
    print("Claim view called, pk:", pk)  # debug
    ticket = get_object_or_404(Ticket, pk=pk)
    # Only allow claiming if unassigned
    if ticket.assigned_to is None:
        ticket.assigned_to = request.user
        ticket.status = Ticket.Status.ASSIGNED   # move to Assigned
        ticket.save()
        TicketActivityLog.objects.create(
            ticket=ticket, action='assigned', actor=request.user,
            details={'to': request.user.get_full_name(), 'status': ticket.status}
        )
        # Optionally create a notification for the agent? Not necessary, but we can add later.
    # Return the updated row or the whole table fragment (for simplicity return the whole table)
    tickets = Ticket.objects.filter(assigned_to__isnull=True).exclude(
        status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]
    ).order_by('-created_at')
    return render(request, 'partials/agent_ticket_table.html', {'tickets': tickets})

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

@login_required
def agent_ticket_conversation(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    # Only agents, team leads, admins can view this page
    if request.user.role not in [User.Role.AGENT, User.Role.TEAM_LEAD, User.Role.ADMIN, User.Role.SUPERADMIN]:
        return HttpResponse(status=403)
    comments = ticket.comments.all().order_by('created_at')
    form = CommentForm()   # we already have this form
    return render(request, 'agent/ticket_conversation.html', {
        'ticket': ticket,
        'comments': comments,
        'form': form,
        # 'followers': followers,
    })

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

        # Log the comment itself
        TicketActivityLog.objects.create(
            ticket=ticket,
            action='commented',
            actor=request.user,
            details={
                'visibility': comment.visibility,
                'body': comment.body[:200]      # keep it short
            }
        )

        # --- AUTOMATION ---
        old_status = ticket.status
        if comment.visibility == 'PUBLIC':
            if old_status in [Ticket.Status.ASSIGNED, Ticket.Status.IN_PROGRESS,
                              Ticket.Status.PENDING_USER, Ticket.Status.NEW,
                              Ticket.Status.TRIAGED]:
                ticket.status = Ticket.Status.IN_PROGRESS
                ticket.save()
                # Log the automatic status change
                if old_status != ticket.status:
                    TicketActivityLog.objects.create(
                        ticket=ticket,
                        action='status_changed',
                        actor=request.user,          # agent who replied
                        details={'from': old_status, 'to': ticket.status}
                    )

    comments = ticket.comments.all().order_by('created_at')
    return render(request, 'partials/conversation_timeline.html', {
        'ticket': ticket,
        'comments': comments,
    })

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
    return HttpResponse(status=204)   # No content, just success

@login_required
def ticket_details_panel(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    # followers list – we'll just pass all agents for now (placeholder)
    followers = User.objects.filter(role__in=['AGENT','TEAM_LEAD'])[:5]  # dummy
    return render(request, 'partials/ticket_details_panel.html', {
        'ticket': ticket,
        'followers': followers,
    })

@login_required
@require_POST
def edit_subject(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    new_title = request.POST.get('title', '').strip()
    if new_title:
        ticket.title = new_title
        ticket.save()
    return render(request, 'partials/subject_display.html', {'ticket': ticket})

@login_required
def assign_popover(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    agents = User.objects.filter(role__in=['AGENT', 'TEAM_LEAD'])[:10]
    return render(request, 'partials/popovers/assign_popover.html', {
        'ticket': ticket,
        'agents': agents,
    })

@login_required
@require_POST
def assign_to_me(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    ticket.assigned_to = request.user
    ticket.save()
    return render(request, 'partials/ticket_details_assignee.html', {'ticket': ticket})

@login_required
@require_POST
def assign_specific(request, pk, user_pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    agent = get_object_or_404(User, pk=user_pk)
    ticket.assigned_to = agent
    ticket.save()
    return render(request, 'partials/ticket_details_assignee.html', {'ticket': ticket})

@login_required
@require_POST
def remove_follower(request, ticket_pk, user_pk):
    # For now, we’re not storing followers in DB; we can skip or return empty
    return HttpResponse(status=204)

@login_required
def add_follower_popover(request, ticket_pk):
    # similar popover but for followers
    return render(request, 'partials/popovers/add_follower_popover.html', {
        'ticket': get_object_or_404(Ticket, pk=ticket_pk),
        'agents': User.objects.filter(role__in=['AGENT','TEAM_LEAD'])[:10],
    })

def edit_group_popover(request, pk):
    return render(request, 'partials/popovers/empty.html')

def edit_type_popover(request, pk):
    return render(request, 'partials/popovers/empty.html')

def edit_priority_popover(request, pk):
    return render(request, 'partials/popovers/empty.html')

def add_tag_popover(request, pk):
    return render(request, 'partials/popovers/empty.html')

def remove_tag(request, pk, tag_pk):
    # remove tag logic
    return HttpResponse(status=204)

@login_required
def macro_list(request):
    macros = Macro.objects.all()
    return render(request, 'partials/macro_dropdown.html', {'macros': macros})

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
            # Log and update each ticket individually
            for ticket in tickets:
                old_status = ticket.status
                ticket.status = value
                ticket.save()
                TicketActivityLog.objects.create(
                    ticket=ticket,
                    action='status_changed',
                    actor=request.user,
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
                    ticket=ticket,
                    action='assigned',
                    actor=request.user,
                    details={
                        'from': old_assignee.get_full_name() if old_assignee else 'Unassigned',
                        'to': agent.get_full_name(),
                        'method': 'bulk'
                    }
                )

    # Return the appropriate table fragment based on source
    source = request.POST.get('source', 'unassigned')
    if source == 'assigned':
        tickets = Ticket.objects.filter(
            assigned_to=request.user
        ).exclude(
            status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]
        ).order_by('-created_at')
    else:
        tickets = Ticket.objects.filter(
            assigned_to__isnull=True
        ).exclude(
            status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]
        ).order_by('-created_at')

    assignable_agents = User.objects.filter(role__in=['AGENT', 'TEAM_LEAD']).only(
        'pk', 'first_name', 'last_name', 'email'
    )
    return render(request, 'partials/agent_ticket_table.html', {
        'tickets': tickets,
        'assignable_agents': assignable_agents,
        'status_choices': Ticket.Status.choices,
    })

@login_required
def team_queue(request):
    if request.user.role != 'TEAM_LEAD':
        return HttpResponse(status=403)
    team_members = User.objects.filter(department=request.user.department, role='AGENT')
    tickets = Ticket.objects.filter(
        assigned_to__in=team_members
    ).exclude(
        status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]
    ).order_by('-created_at')

    agent_id = request.GET.get('agent')
    if agent_id:
        tickets = tickets.filter(assigned_to_id=agent_id)

    context = {
        'tickets': tickets,
        'team_members': team_members,
        'selected_agent': agent_id,
    }
    return render(request, 'partials/team_queue.html', context)


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
        ticket=ticket,
        action='assigned',
        actor=request.user,
        details={
            'from': old_assignee.get_full_name() if old_assignee else 'Unassigned',
            'to': agent.get_full_name()
        }
    )
    return JsonResponse({'status': 'ok'})


@login_required
def audit_log(request):
    if request.user.role not in ['TEAM_LEAD', 'ADMIN', 'SUPERADMIN']:
        return HttpResponse(status=403)

    logs = TicketActivityLog.objects.select_related('ticket', 'actor').all()

    # Team Leads see only their department's agents' tickets
    if request.user.role == 'TEAM_LEAD':
        team_members = User.objects.filter(department=request.user.department, role='AGENT')
        logs = logs.filter(
            Q(ticket__assigned_to__in=team_members) |
            Q(ticket__requester__in=team_members)
        )

    # Filters
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
    }
    return render(request, 'partials/audit_log.html', context)

def kb_suggestions(request):
    # Will be implemented in Sprint 5
    return render(request, 'partials/kb_suggestions.html', {'articles': []})

