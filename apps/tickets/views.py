import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from .forms import TicketForm, CommentForm
from .models import Ticket, TicketComment, Macro
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

        # --- AUTOMATION ---
        if comment.visibility == 'PUBLIC':
            # Agent replied: move to IN_PROGRESS if currently ASSIGNED or IN_PROGRESS or PENDING_USER
            if ticket.status in [Ticket.Status.ASSIGNED, Ticket.Status.IN_PROGRESS, Ticket.Status.PENDING_USER]:
                ticket.status = Ticket.Status.IN_PROGRESS
                ticket.save()
            # If agent replies while NEW/TRIAGED, we could also set to IN_PROGRESS?
            # We'll also cover that case.
            elif ticket.status == Ticket.Status.NEW or ticket.status == Ticket.Status.TRIAGED:
                ticket.status = Ticket.Status.IN_PROGRESS
                ticket.save()

    comments = ticket.comments.all().order_by('created_at')
    return render(request, 'partials/conversation_timeline.html', {
        'ticket': ticket, 
        'comments': comments
        })

@login_required
@require_POST
def update_status(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    new_status = request.GET.get('status')
    if new_status and new_status in dict(Ticket.Status.choices):
        ticket.status = new_status
        ticket.save()
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
            tickets.update(status=value)
    elif action == 'assign':
        # Only team leads/admins can bulk assign
        if request.user.role not in ['TEAM_LEAD', 'ADMIN', 'SUPERADMIN']:
            return HttpResponse(status=403)
        if value.isdigit():
            agent = get_object_or_404(User, pk=int(value))
            tickets.update(assigned_to=agent)

    # Return the updated table fragment based on the referer? We'll just return the full table for now.
    # For simplicity, we'll regenerate the same list as the current view.
    # Determine which queue: unassigned or assigned based on request? We'll just render the same partial
    # that the calling page expects. However, since the bulk action may be called from either page,
    # we'll return a generic agent_ticket_table with tickets from a query matching the original list.
    # Better approach: we can pass a query param indicating the source, or just return all unassigned (if called from unassigned)
    # and assigned (if from assigned). But we don't have that info. We'll modify the fetch call in the template
    # to include a hidden field with the source. Let's do that.

    source = request.POST.get('source', 'unassigned')  # we'll set it in the JS
    if source == 'assigned':
        tickets = Ticket.objects.filter(assigned_to=request.user).exclude(
            status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]).order_by('-created_at')
    else:
        tickets = Ticket.objects.filter(assigned_to__isnull=True).exclude(
            status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]).order_by('-created_at')

    assignable_agents = User.objects.filter(role__in=['AGENT', 'TEAM_LEAD']).only('pk', 'first_name', 'last_name', 'email')
    return render(request, 'partials/agent_ticket_table.html', {
        'tickets': tickets,
        'assignable_agents': assignable_agents,
        'status_choices': Ticket.Status.choices,
    })


def kb_suggestions(request):
    # Will be implemented in Sprint 5
    return render(request, 'partials/kb_suggestions.html', {'articles': []})

