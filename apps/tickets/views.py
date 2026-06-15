import random, hashlib, os, re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.management import call_command
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Avg, Q, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings
from .forms import TicketForm, CommentForm
from .models import Ticket, TicketComment, Macro, TicketActivityLog, SLA, EscalationRule, BusinessCalendar, Attachment, Asset, RemoteConnector, RemoteSession
from apps.accounts.models import User
from apps.common.models import Notification
from bs4 import BeautifulSoup

# ==========================================================================
# HELPER FUNCTIONS
# ==========================================================================

def clean_comment_body(body):
    """
    Cleans HTML content from the rich text editor before saving.
    - Removes empty div/p/span tags.
    - Replaces <br> tags with newlines.
    - Collapses multiple consecutive newlines into a single newline.
    - Strips leading/trailing whitespace.
    Returns None if the cleaned body is empty (used to reject empty comments).
    """
    if not body:
        return None
    soup = BeautifulSoup(body, 'html.parser')
    
    # Remove empty block tags that contain no text and no formatting children
    for tag in soup.find_all():
        if tag.name in ['div', 'p', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            if not tag.get_text(strip=True) and not tag.find_all(['strong', 'em', 'br']):
                tag.decompose()
    
    # Replace <br> with newline characters (they will be turned back into <br> by linebreaksbr filter)
    for br in soup.find_all('br'):
        br.replace_with('\n')
    
    cleaned = str(soup)
    cleaned = re.sub(r'\n\s*\n+', '\n', cleaned)
    cleaned = cleaned.strip()
    
    if not cleaned or cleaned == '':
        return None
    return cleaned

def get_sidebar_template(user):
    """
    Returns the correct sidebar partial template based on the user's role.
    Used in all dashboard views to load the appropriate navigation sidebar.
    """
    mapping = {
        'END_USER': 'partials/sidebar_end_user.html',
        'AGENT': 'partials/sidebar_agent.html',
        'TEAM_LEAD': 'partials/sidebar_team_lead.html',
        'ADMIN': 'partials/sidebar_admin.html',
        'SUPERADMIN': 'partials/sidebar_superadmin.html',
        'APPROVER': 'partials/sidebar_approver.html',
    }
    return mapping.get(user.role, 'partials/sidebar_end_user.html')

def apply_sla(ticket):
    """
    Sets the response_due_at and resolution_due_at fields on a ticket
    based on the SLA policy configured for its priority.
    Called after ticket creation and when priority changes.
    """
    try:
        sla = SLA.objects.get(priority=ticket.priority)
    except SLA.DoesNotExist:
        return
    now = timezone.now()
    ticket.response_due_at = now + timedelta(minutes=sla.response_minutes)
    ticket.resolution_due_at = now + timedelta(minutes=sla.resolution_minutes)
    ticket.save(update_fields=['response_due_at', 'resolution_due_at'])

# Allowed MIME types for file attachments
ALLOWED_MIMES = [
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/plain',
    'application/zip',
]
MAX_SIZE_MB = 10

def save_attachments(ticket, files, author, comment=None):
    """
    Validates and saves uploaded file attachments.
    - Skips files that exceed MAX_SIZE_MB or have disallowed MIME types.
    - Computes SHA-256 hash for integrity checking.
    - Associates attachments with a ticket and optionally a specific comment.
    Returns list of created Attachment objects.
    """
    created = []
    for f in files:
        if f.size > MAX_SIZE_MB * 1024 * 1024:
            continue
        mime = f.content_type.split(';')[0].strip().lower()
        if mime not in ALLOWED_MIMES:
            continue
        sha = hashlib.sha256()
        for chunk in f.chunks():
            sha.update(chunk)
        f.seek(0)
        att = Attachment.objects.create(
            ticket=ticket,
            comment=comment,
            file=f,
            filename=f.name,
            uploaded_by=author,
            content_type=mime,
            size=f.size,
            hash=sha.hexdigest(),
        )
        created.append(att)
    return created

# ==========================================================================
# TICKET CREATION & LISTING VIEWS (End Users)
# ==========================================================================

@login_required
def create_ticket(request):
    """
    Handles creation of a new ticket (incident or service request).
    - GET: displays the appropriate form (incident_form or service_request_form).
    - POST: validates form, generates a unique ticket number, saves ticket,
            attaches files, applies SLA, and redirects to ticket detail page.
    """
    ticket_type = request.GET.get('type', 'INCIDENT').upper()
    if ticket_type not in ['INCIDENT', 'SERVICE_REQUEST']:
        ticket_type = 'INCIDENT'

    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.requester = request.user
            ticket.type = ticket_type

            # Generate unique ticket number (e.g., TK#1234 or SRV#5678)
            prefix = 'TK' if ticket.type == Ticket.Type.INCIDENT else 'SRV'
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

            files = request.FILES.getlist('attachments')
            if files:
                save_attachments(ticket, files, request.user)

            # If it's a service request, set status to PENDING_APPROVAL
            if ticket.type == Ticket.Type.SERVICE_REQUEST:
                ticket.status = Ticket.Status.PENDING_APPROVAL
                ticket.save(update_fields=['status'])
            apply_sla(ticket)

            return redirect('tickets:detail', pk=ticket.pk)
    else:
        form = TicketForm(initial={'type': ticket_type})

    template = 'requester/incident_form.html' if ticket_type == 'INCIDENT' else 'requester/service_request_form.html'
    return render(request, template, {'form': form, 'ticket_type': ticket_type})

@login_required
@require_POST
def cancel_ticket(request, pk):
    """
    Allows an end user to cancel a ticket that is still in NEW or TRIAGED status.
    - Closes the ticket and logs the action.
    - If the request is HTMX, returns the updated ticket list partial.
    """
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
        if status_filter and status_filter.upper() in dict(Ticket.Status.choices):
            tickets = tickets.filter(status=status_filter.upper())
        paginator = Paginator(tickets, 10)
        page_number = request.POST.get('page', 1)
        try:
            page_obj = paginator.page(page_number)
        except (PageNotAnInteger, EmptyPage):
            page_obj = paginator.page(1)
        context = {
            'tickets': page_obj,
            'current_status': status_filter,
            'status_choices': Ticket.Status.choices,
        }
        return render(request, 'partials/ticket_list_partial.html', context)
    return redirect('tickets:my_list')

@login_required
def my_ticket_list(request):
    """
    Displays a list of tickets created by the logged‑in end user.
    Supports filtering by status (OPEN/CLOSED or specific status).
    Uses HTMX for pagination and filter updates.
    """
    tickets = Ticket.objects.filter(requester=request.user).order_by('-created_at')
    status_filter = request.GET.get('status', '')
    base = request.GET.get('base', '')
    open_statuses = ['NEW', 'TRIAGED', 'ASSIGNED', 'IN_PROGRESS', 'PENDING_USER', 'PENDING_VENDOR', 'APPROVED']
    closed_statuses = ['RESOLVED', 'CLOSED']

    if status_filter == 'OPEN':
        tickets = tickets.filter(status__in=open_statuses)
    elif status_filter == 'CLOSED':
        tickets = tickets.filter(status__in=closed_statuses)
    elif status_filter and status_filter.upper() in dict(Ticket.Status.choices):
        tickets = tickets.filter(status=status_filter.upper())

    paginator = Paginator(tickets, 10)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    all_choices = Ticket.Status.choices
    if base == 'OPEN':
        status_choices = [('NEW','New'), ('TRIAGED','Triaged'), ('ASSIGNED','Assigned'),
                          ('IN_PROGRESS','In Progress'), ('PENDING_USER','Pending User'),
                          ('PENDING_VENDOR','Pending Vendor'), ('APPROVED','Approved')]
    elif base == 'CLOSED':
        status_choices = [('RESOLVED','Resolved'), ('CLOSED','Closed')]
    else:
        status_choices = all_choices

    base_status = base if base in ['OPEN','CLOSED'] else ''
    explicit = request.GET.get('explicit') == '1'

    context = {
        'tickets': page_obj,
        'current_status': status_filter or '',
        'status_choices': status_choices,
        'sidebar_template': get_sidebar_template(request.user),
        'base_status': base_status,
        'explicit': explicit,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'partials/ticket_list_partial.html', context)
    return render(request, 'requester/ticket_list.html', context)

@login_required
def ticket_detail(request, pk):
    """
    Unified ticket conversation page for both requesters and agents.
    - GET: displays the conversation timeline and comment form.
    - POST (HTMX): accepts a new public comment from the requester,
      cleans the HTML body, saves attachments, updates ticket status if needed,
      and returns the updated timeline partial.
    The 'is_agent' flag controls visibility of agent‑only UI elements.
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.user != ticket.requester and request.user.role not in ['AGENT', 'TEAM_LEAD', 'ADMIN', 'SUPERADMIN']:
        return redirect('dashboard')

    # Handle comment submission from requester
    if request.method == 'POST' and request.headers.get('HX-Request'):
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.ticket = ticket
            comment.author = request.user
            comment.visibility = 'PUBLIC'
            cleaned_body = clean_comment_body(comment.body)
            if cleaned_body is None:
                return HttpResponse(status=400)   # empty message
            comment.body = cleaned_body
            comment.save()

            files = request.FILES.getlist('attachments')
            if files:
                save_attachments(ticket, files, request.user, comment=comment)

            if ticket.status == Ticket.Status.PENDING_USER:
                ticket.status = Ticket.Status.IN_PROGRESS
                ticket.save()
                TicketActivityLog.objects.create(
                    ticket=ticket, action='status_changed', actor=request.user,
                    details={'from': Ticket.Status.PENDING_USER, 'to': Ticket.Status.IN_PROGRESS}
                )

            comments = ticket.comments.prefetch_related('attachment_set').all().order_by('created_at')
            initial_attachments = ticket.attachments.filter(comment__isnull=True)
            return render(request, 'partials/conversation_timeline.html', {
                'ticket': ticket,
                'comments': comments,
                'initial_attachments': initial_attachments,
            })
        else:
            return HttpResponse(status=422)

    # GET request – render conversation page
    comments = ticket.comments.all().order_by('created_at')
    initial_attachments = ticket.attachments.filter(comment__isnull=True)
    user_attachments = ticket.attachments.filter(uploaded_by__role='END_USER')
    agent_attachments = ticket.attachments.filter(
        uploaded_by__role__in=['AGENT', 'TEAM_LEAD', 'ADMIN', 'SUPERADMIN']
    )
    form = CommentForm()
    is_agent = request.user.role in ['AGENT', 'TEAM_LEAD', 'ADMIN', 'SUPERADMIN']

    return render(request, 'agent/ticket_conversation.html', {
        'ticket': ticket,
        'comments': comments,
        'form': form,
        'initial_attachments': initial_attachments,
        'user_attachments': user_attachments,
        'agent_attachments': agent_attachments,
        'sidebar_template': get_sidebar_template(request.user),
        'is_agent': is_agent,
    })

# ==========================================================================
# AGENT QUEUES & TICKET MANAGEMENT
# ==========================================================================

@login_required
def unassigned_queue(request):
    """
    Displays all tickets that are not assigned to anyone,
    excluding resolved, closed, and pending approval tickets.
    Agents can claim tickets directly from this view.
    """
    tickets = Ticket.objects.filter(
        assigned_to__isnull=True
    ).exclude(
        status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED, Ticket.Status.PENDING_APPROVAL]
    ).order_by('-created_at')

    assignable_agents = User.objects.filter(role__in=['AGENT', 'TEAM_LEAD', 'ADMIN', 'SUPERADMIN']).only('pk', 'first_name', 'last_name', 'email')

    context = {
        'tickets': tickets,
        'assignable_agents': assignable_agents,
        'status_choices': Ticket.Status.choices,
        'sidebar_template': get_sidebar_template(request.user),
    }
    return render(request, 'agent/unassigned_queue.html', context)

@login_required
def assigned_to_me(request):
    """
    Displays all tickets assigned to the logged‑in agent,
    excluding resolved, closed, and pending approval tickets.
    """
    tickets = Ticket.objects.filter(
        assigned_to=request.user
    ).exclude(
        status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED, Ticket.Status.PENDING_APPROVAL]
    ).order_by('-created_at')

    assignable_agents = User.objects.filter(role__in=['AGENT', 'TEAM_LEAD', 'ADMIN', 'SUPERADMIN']).only('pk', 'first_name', 'last_name', 'email')

    context = {
        'tickets': tickets,
        'assignable_agents': assignable_agents,
        'status_choices': Ticket.Status.choices,
        'sidebar_template': get_sidebar_template(request.user),
    }
    return render(request, 'agent/assigned_to_me.html', context)

@login_required
def claim_ticket(request, pk):
    """
    Allows an agent to claim an unassigned ticket.
    Assigns the ticket to the current user and sets status to ASSIGNED.
    Returns the updated agent ticket table partial (HTMX).
    """
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

    assignable_agents = User.objects.filter(
        role__in=['AGENT', 'TEAM_LEAD', 'ADMIN', 'SUPERADMIN']
    ).only('pk', 'first_name', 'last_name', 'email')

    return render(request, 'partials/agent_ticket_table.html', {
        'tickets': tickets,
        'assignable_agents': assignable_agents,
        'status_choices': Ticket.Status.choices,
    })

@login_required
def agent_ticket_detail(request, pk):
    """
    Returns a slide‑over panel with ticket details and comments.
    Used when an agent clicks the "eye" icon on a ticket row.
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.user.role not in [User.Role.AGENT, User.Role.TEAM_LEAD, User.Role.ADMIN, User.Role.SUPERADMIN]:
        return HttpResponse(status=403)
    comments = ticket.comments.all().order_by('created_at')
    user_attachments = ticket.attachments.filter(uploaded_by__role='END_USER')
    agent_attachments = ticket.attachments.filter(
        uploaded_by__role__in=['AGENT', 'TEAM_LEAD', 'ADMIN', 'SUPERADMIN']
    )
    return render(request, 'partials/ticket_slideover.html', {
        'ticket': ticket,
        'comments': comments,
        'user_attachments': user_attachments,
        'agent_attachments': agent_attachments,
    })

@login_required
def agent_ticket_conversation(request, pk):
    """
    Full‑page conversation view for agents (and admins).
    Renders the same template as ticket_detail but with is_agent=True.
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.user.role not in [User.Role.AGENT, User.Role.TEAM_LEAD, User.Role.ADMIN, User.Role.SUPERADMIN]:
        return HttpResponse(status=403)
    comments = ticket.comments.all().order_by('created_at')
    form = CommentForm()
    initial_attachments = ticket.attachments.filter(comment__isnull=True)
    user_attachments = ticket.attachments.filter(uploaded_by__role='END_USER')
    agent_attachments = ticket.attachments.filter(
        uploaded_by__role__in=['AGENT', 'TEAM_LEAD', 'ADMIN', 'SUPERADMIN']
    )
    return render(request, 'agent/ticket_conversation.html', {
        'ticket': ticket,
        'comments': comments,
        'form': form,
        'initial_attachments': initial_attachments,
        'user_attachments': user_attachments,
        'agent_attachments': agent_attachments,
        'sidebar_template': get_sidebar_template(request.user),
        'is_agent': True,
    })

@login_required
@require_POST
def add_comment_conversation(request, pk):
    """
    Handles agent comments (public or internal) on a ticket.
    - Cleans the HTML body using BeautifulSoup.
    - Saves attachments.
    - Updates ticket status to IN_PROGRESS if a public comment is added.
    - Returns the updated conversation timeline partial (HTMX).
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.ticket = ticket
        comment.author = request.user
        comment.visibility = request.POST.get('visibility', 'PUBLIC').upper()
        if comment.visibility not in ['PUBLIC', 'INTERNAL']:
            comment.visibility = 'PUBLIC'
        cleaned_body = clean_comment_body(comment.body)
        if cleaned_body is None:
            return HttpResponse(status=400)
        comment.body = cleaned_body
        comment.save()

        files = request.FILES.getlist('attachments')
        if files:
            created = save_attachments(ticket, files, request.user, comment=comment)
            comment = TicketComment.objects.get(pk=comment.pk)

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

    comments = ticket.comments.prefetch_related('attachment_set').all().order_by('created_at')
    initial_attachments = ticket.attachments.filter(comment__isnull=True)
    return render(request, 'partials/conversation_timeline.html', {
        'ticket': ticket,
        'comments': comments,
        'initial_attachments': initial_attachments, 
    })

@login_required
@require_POST
def update_status(request, pk):
    """
    Changes the status of a ticket. Only agents, team leads, admins, and superadmins can do this.
    The new status is passed as a GET parameter 'status'.
    Logs the change in TicketActivityLog.
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.user.role not in [User.Role.AGENT, User.Role.TEAM_LEAD, User.Role.ADMIN, User.Role.SUPERADMIN]:
        return HttpResponse(status=403)
    
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

# ==========================================================================
# TICKET DETAILS PANEL & METADATA EDITING
# ==========================================================================

@login_required
def ticket_details_panel(request, pk):
    """
    Returns the right‑hand details panel (assignee, metadata, attachments)
    that slides in on the conversation page.
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    followers = User.objects.filter(role__in=['AGENT','TEAM_LEAD'])[:5]
    user_attachments = ticket.attachments.filter(uploaded_by__role='END_USER')
    agent_attachments = ticket.attachments.filter(
        uploaded_by__role__in=['AGENT', 'TEAM_LEAD', 'ADMIN', 'SUPERADMIN']
    )
    return render(request, 'partials/ticket_details_panel.html', {
        'ticket': ticket,
        'followers': followers,
        'user_attachments': user_attachments,
        'agent_attachments': agent_attachments,
    })

@login_required
@require_POST
def edit_subject(request, pk):
    """
    Edits the ticket title inline (subject).
    Returns the updated subject display partial.
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    new_title = request.POST.get('title', '').strip()
    if new_title:
        ticket.title = new_title
        ticket.save()
    return render(request, 'partials/subject_display.html', {'ticket': ticket})

# ==========================================================================
# ASSIGNMENT POPOVERS AND ACTIONS
# ==========================================================================

@login_required
def assign_popover(request, pk):
    """
    Returns a popover with a list of assignable agents (Agent, Team Lead, Admin, Superadmin)
    so the agent can reassign the ticket.
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    agents = User.objects.filter(role__in=['AGENT', 'TEAM_LEAD', 'ADMIN', 'SUPERADMIN'])[:10]
    return render(request, 'partials/popovers/assign_popover.html', {'ticket': ticket, 'agents': agents})

@login_required
@require_POST
def assign_to_me(request, pk):
    """
    Assigns the ticket to the current user.
    Returns the updated assignee display partial.
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    ticket.assigned_to = request.user
    ticket.save()
    return render(request, 'partials/ticket_details_assignee.html', {'ticket': ticket})

@login_required
@require_POST
def assign_specific(request, pk, user_pk):
    """
    Assigns the ticket to a specific user (by primary key).
    Returns the updated assignee display partial.
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    agent = get_object_or_404(User, pk=user_pk)
    ticket.assigned_to = agent
    ticket.save()
    return render(request, 'partials/ticket_details_assignee.html', {'ticket': ticket})

# ==========================================================================
# FOLLOWER STUBS (not fully implemented)
# ==========================================================================

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

# Placeholder popovers
def edit_group_popover(request, pk): return render(request, 'partials/popovers/empty.html')
def edit_type_popover(request, pk): return render(request, 'partials/popovers/empty.html')
def edit_priority_popover(request, pk): return render(request, 'partials/popovers/empty.html')
def add_tag_popover(request, pk): return render(request, 'partials/popovers/empty.html')
def remove_tag(request, pk, tag_pk): return HttpResponse(status=204)

# ==========================================================================
# MACROS
# ==========================================================================

@login_required
def macro_list(request):
    """
    Returns a dropdown list of macros (predefined reply templates) for agents.
    Used in the conversation composer.
    """
    macros = Macro.objects.all()
    return render(request, 'partials/macro_dropdown.html', {'macros': macros})

# ==========================================================================
# BULK ACTIONS (for ticket queues)
# ==========================================================================

@login_required
@require_POST
def bulk_action(request):
    """
    Performs bulk status change or assignment on multiple tickets.
    Only Team Leads, Admins, and Superadmins can bulk‑assign.
    Returns the updated agent ticket table partial.
    """
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

    assignable_agents = User.objects.filter(role__in=['AGENT', 'TEAM_LEAD', 'ADMIN', 'SUPERADMIN']).only('pk', 'first_name', 'last_name', 'email')
    return render(request, 'partials/agent_ticket_table.html', {
        'tickets': tickets,
        'assignable_agents': assignable_agents,
        'status_choices': Ticket.Status.choices,
    })

# ==========================================================================
# TEAM LEAD QUEUE & REASSIGNMENT
# ==========================================================================

@login_required
def team_queue(request):
    """
    Team Lead view: shows all tickets assigned to agents in the same department.
    Allows filtering by individual agent.
    """
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

@login_required
@require_POST
def team_reassign(request, pk):
    """
    Allows a Team Lead to reassign a ticket to another agent in their team.
    Returns JSON status.
    """
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

# ==========================================================================
# AUDIT LOG
# ==========================================================================

@login_required
def audit_log(request):
    """
    Displays the audit trail (ticket activity log) for users with sufficient permissions.
    Team Leads see only activity on tickets from their department.
    Admins and Superadmins see all activity.
    """
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
    if action: logs = logs.filter(action=action)
    if ticket_id: logs = logs.filter(ticket__number__icontains=ticket_id)
    logs = logs.order_by('-created_at')[:100]
    context = {
        'logs': logs,
        'action_choices': ['created', 'status_changed', 'assigned', 'unassigned', 'commented'],
        'sidebar_template': get_sidebar_template(request.user),
    }
    return render(request, 'partials/audit_log.html', context)

# ==========================================================================
# REPORTS DASHBOARD (Charts & KPIs)
# ==========================================================================

@login_required
def reports_dashboard(request):
    """
    Renders the reports page with SLA compliance, ticket volume, and priority charts.
    Data is filtered by role (Admin/Superadmin see all, Team Lead sees only their team).
    """
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

# ==========================================================================
# EXTERNAL CRON TRIGGERS (SLA & CLEANUP)
# ==========================================================================

@csrf_exempt
def trigger_sla_processing(request):
    """
    External endpoint (secured with a secret) to trigger the SLA processing command.
    Used by cron‑job.org to automate SLA monitoring.
    """
    secret = request.GET.get('secret')
    if secret != 'jkeihwihivkgyg678448bhct36gysyvy!!gygrv':
        return HttpResponse(status=403)
    try:
        call_command('process_sla')
        return HttpResponse('SLA processed OK', status=200)
    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=500)

@csrf_exempt
def trigger_cleanup(request):
    """
    External endpoint to trigger the cleanup of inactive users.
    """
    secret = request.GET.get('secret')
    if secret != 'jkeihwihivkgyg678448bhct36gysyvy!!gygrv':
        return HttpResponse(status=403)
    try:
        call_command('cleanup_inactive_users')
        return HttpResponse('Cleanup completed', status=200)
    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=500)

# ==========================================================================
# PLACEHOLDER / STATIC PAGES
# ==========================================================================

@login_required
def catalogue(request):
    if request.user.role not in ['ADMIN', 'SUPERADMIN']: return HttpResponse(status=403)
    return render(request, 'admin/catalogue.html', {'sidebar_template': get_sidebar_template(request.user)})

@login_required
def connectors(request):
    """
    Admin/Superadmin configuration page for remote connectors (Quick Assist, etc.).
    Lists all connectors and allows editing.
    """
    if request.user.role not in ['ADMIN', 'SUPERADMIN']:
        return HttpResponse(status=403)
    connectors_list = RemoteConnector.objects.all().order_by('name')
    return render(request, 'admin/connectors.html', {
        'connectors': connectors_list,
        'sidebar_template': get_sidebar_template(request.user),
    })

@login_required
@require_http_methods(['GET', 'POST'])
def connector_edit(request, pk):
    """
    Edit a specific remote connector: enable/disable and update instructions.
    """
    if request.user.role not in ['ADMIN', 'SUPERADMIN']:
        return HttpResponse(status=403)
    connector = get_object_or_404(RemoteConnector, pk=pk)
    if request.method == 'POST':
        connector.is_active = request.POST.get('is_active') == 'on'
        connector.instructions_for_requester = request.POST.get('instructions_for_requester', '')
        connector.instructions_for_agent = request.POST.get('instructions_for_agent', '')
        connector.save()
        return redirect('tickets:connectors')
    return render(request, 'admin/connector_form.html', {
        'connector': connector,
        'sidebar_template': get_sidebar_template(request.user),
    })

@login_required
def assets(request):
    """
    Asset list (CMDB‑lite) – view all assets. Accessible to Agents, Team Leads, Admins, Superadmins.
    """
    if request.user.role not in ['ADMIN', 'SUPERADMIN', 'AGENT', 'TEAM_LEAD']:
        return HttpResponse(status=403)
    assets_list = Asset.objects.all().order_by('-created_at')
    paginator = Paginator(assets_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'tickets/asset_list.html', {
        'assets': page_obj,
        'sidebar_template': get_sidebar_template(request.user),
    })

@login_required
@require_http_methods(['GET', 'POST'])
def asset_create(request):
    """
    Create a new asset (Admin/Superadmin only).
    """
    if request.user.role not in ['ADMIN', 'SUPERADMIN']:
        return HttpResponse(status=403)
    if request.method == 'POST':
        name = request.POST.get('name')
        asset_type = request.POST.get('asset_type')
        serial = request.POST.get('serial_number')
        assigned_to_id = request.POST.get('assigned_to')
        status = request.POST.get('status')
        purchase_date = request.POST.get('purchase_date') or None
        notes = request.POST.get('notes')
        Asset.objects.create(
            name=name, asset_type=asset_type, serial_number=serial,
            assigned_to_id=assigned_to_id or None, status=status,
            purchase_date=purchase_date, notes=notes
        )
        return redirect('tickets:assets')
    users = User.objects.filter(role__in=['END_USER', 'AGENT'])
    return render(request, 'tickets/asset_form.html', {
        'users': users,
        'sidebar_template': get_sidebar_template(request.user),
    })

@login_required
def asset_edit(request, pk):
    """
    (Optional) Edit an existing asset. Not yet implemented.
    """
    pass

# ==========================================================================
# REMOTE SESSION REQUESTS (Quick Assist integration)
# ==========================================================================

@login_required
@require_POST
def request_remote_session(request, pk):
    """
    Initiates a remote session request from an agent to the ticket requester.
    - Creates a RemoteSession record (status=REQUESTED).
    - Adds a public comment on the ticket.
    - Sends an in‑app notification to the requester.
    - Sends an email to the requester with a link to accept the session.
    - Logs the action in the activity log.
    Only agents, team leads, admins, and superadmins can call this.
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.user.role not in [User.Role.AGENT, User.Role.TEAM_LEAD, User.Role.ADMIN, User.Role.SUPERADMIN]:
        return HttpResponse(status=403)

    # Get the first active remote connector (e.g., Quick Assist)
    connector = RemoteConnector.objects.filter(is_active=True).first()
    if not connector:
        return HttpResponse("No active remote connector configured.", status=400)

    # Check if there's already a pending or active session for this ticket
    existing = RemoteSession.objects.filter(ticket=ticket, status__in=['REQUESTED', 'ACCEPTED', 'STARTED']).first()
    if existing:
        return JsonResponse({'error': 'A remote session is already pending or in progress.'}, status=400)
    
    session = RemoteSession.objects.create(
        ticket=ticket,
        requester=ticket.requester,
        agent=request.user,
        connector=connector,
        status='REQUESTED'
    )

    # Add a public comment to the ticket timeline
    TicketComment.objects.create(
        ticket=ticket,
        author=request.user,
        body=f"Remote session requested via {connector.name}. Please check your notifications to accept.",
        visibility='PUBLIC'
    )

    # Send in‑app notification
    Notification.objects.create(
        recipient=ticket.requester,
        message=f"Remote session requested for ticket {ticket.number}. Click to accept.",
        url=reverse('tickets:remote_session_detail', args=[session.pk])
    )

    # Send email notification to the requester
    accept_url = request.build_absolute_uri(reverse('tickets:remote_session_detail', args=[session.pk]))
    send_mail(
        subject=f"Remote Session Request – Ticket {ticket.number}",
        message=f"An agent has requested a remote session to help you with ticket {ticket.number}.\n\n"
                f"Please click the link below to accept and view instructions:\n{accept_url}\n\n"
                f"If you did not request this, please ignore this email.\n\n"
                f"– IT Support Team",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[ticket.requester.email],
        fail_silently=True,
    )
    
    TicketActivityLog.objects.create(
        ticket=ticket,
        action='remote_session_requested',
        actor=request.user,
        details={'connector': connector.name, 'session_id': session.pk}
    )
    
    return JsonResponse({'session_id': session.pk, 'status': 'requested'})

@login_required
def remote_session_detail(request, session_pk):
    session = get_object_or_404(RemoteSession, pk=session_pk)
    user = request.user
    if user != session.requester and user != session.agent:
        return HttpResponse(status=403)
    
    if user == session.agent:
        instructions = session.connector.instructions_for_agent
        role = 'agent'
    else:
        instructions = session.connector.instructions_for_requester
        role = 'requester'
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(RemoteSession.STATUS_CHOICES):
            old_status = session.status
            # Handle REJECT from requester
            if new_status == 'REJECTED' and role == 'requester':
                session.status = 'REJECTED'
                session.save()
                # Notify agent
                Notification.objects.create(
                    recipient=session.agent,
                    message=f"{session.requester.get_full_name()} rejected the remote session for ticket {session.ticket.number}.",
                    url=reverse('tickets:remote_session_detail', args=[session.pk])
                )
                TicketActivityLog.objects.create(
                    ticket=session.ticket,
                    action='remote_session_status_change',
                    actor=user,
                    details={'from': old_status, 'to': 'REJECTED', 'session_id': session.pk}
                )
                return redirect('tickets:remote_session_detail', session_pk=session.pk)
            
            # Handle ACCEPT from requester
            elif new_status == 'ACCEPTED' and role == 'requester' and old_status == 'REQUESTED':
                session.status = 'ACCEPTED'
                session.save()
                # Notify agent
                Notification.objects.create(
                    recipient=session.agent,
                    message=f"{session.requester.get_full_name()} accepted the remote session for ticket {session.ticket.number}.",
                    url=reverse('tickets:remote_session_detail', args=[session.pk])
                )
                TicketActivityLog.objects.create(
                    ticket=session.ticket,
                    action='remote_session_status_change',
                    actor=user,
                    details={'from': old_status, 'to': 'ACCEPTED', 'session_id': session.pk}
                )
                return redirect('tickets:remote_session_detail', session_pk=session.pk)
            
            # Handle START with code from agent
            elif new_status == 'STARTED' and role == 'agent' and old_status == 'ACCEPTED':
                code = request.POST.get('quick_assist_code', '').strip()
                if not code or len(code) < 6:
                    # Optionally show error message
                    pass
                else:
                    session.session_code = code
                    session.status = 'STARTED'
                    session.started_at = timezone.now()
                    session.save()
                    # Send automatic public comment on ticket
                    TicketComment.objects.create(
                        ticket=session.ticket,
                        author=request.user,
                        body=f"Remote session code: {code}. Please use this code in Quick Assist to start the session.",
                        visibility='PUBLIC'
                    )
                    # Send email to requester
                    send_mail(
                        subject=f"Remote Session Code – Ticket {session.ticket.number}",
                        message=f"The support agent has started a remote session. Use this code in Quick Assist: {code}\n\n"
                                f"Quick Assist instructions:\n{session.connector.instructions_for_requester}\n\n"
                                f"If you didn't request this, please ignore.",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[session.requester.email],
                        fail_silently=True,
                    )
                    TicketActivityLog.objects.create(
                        ticket=session.ticket,
                        action='remote_session_status_change',
                        actor=user,
                        details={'from': old_status, 'to': 'STARTED', 'session_id': session.pk, 'code': code}
                    )
                    return redirect('tickets:remote_session_detail', session_pk=session.pk)
            
            # Handle END from agent
            elif new_status == 'ENDED' and role == 'agent' and old_status == 'STARTED':
                session.status = 'ENDED'
                session.ended_at = timezone.now()
                session.save()
                TicketActivityLog.objects.create(
                    ticket=session.ticket,
                    action='remote_session_status_change',
                    actor=user,
                    details={'from': old_status, 'to': 'ENDED', 'session_id': session.pk}
                )
                return redirect('tickets:remote_session_detail', session_pk=session.pk)
    
    context = {
        'session': session,
        'instructions': instructions,
        'role': role,
        'sidebar_template': get_sidebar_template(request.user),
    }
    return render(request, 'tickets/remote_session_detail.html', context)

@login_required
def remote_sessions_list(request):
    """
    List all remote sessions relevant to the logged‑in user.
    - Agents see sessions they initiated (as agent).
    - Requesters see sessions requested for their tickets.
    - Admins/Superadmins see all sessions (optional, but we'll filter by role).
    """
    user = request.user
    if user.role in ['ADMIN', 'SUPERADMIN']:
        sessions = RemoteSession.objects.all().order_by('-created_at')
    elif user.role in ['AGENT', 'TEAM_LEAD']:
        sessions = RemoteSession.objects.filter(agent=user).order_by('-created_at')
    else:
        sessions = RemoteSession.objects.filter(requester=user).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(sessions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'sessions': page_obj,
        'sidebar_template': get_sidebar_template(request.user),
    }
    return render(request, 'tickets/remote_sessions_list.html', context)


def kb_suggestions(request):
    return render(request, 'partials/kb_suggestions.html', {'articles': []})

# ==========================================================================
# APPROVER VIEWS (for service requests)
# ==========================================================================

@login_required
def approver_dashboard(request):
    if request.user.role != User.Role.APPROVER: return HttpResponse(status=403)
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
    if request.user.role != User.Role.APPROVER: return HttpResponse(status=403)
    tickets = Ticket.objects.filter(status=Ticket.Status.PENDING_APPROVAL).order_by('-created_at')
    return render(request, 'partials/approver_pending.html', {'tickets': tickets, 'sidebar_template': get_sidebar_template(request.user)})

@login_required
def approver_history(request):
    if request.user.role != User.Role.APPROVER: return HttpResponse(status=403)
    logs = TicketActivityLog.objects.filter(
        actor=request.user, action__in=['approved', 'rejected']
    ).select_related('ticket').order_by('-created_at')[:50]
    return render(request, 'partials/approver_history.html', {'logs': logs, 'sidebar_template': get_sidebar_template(request.user)})

@login_required
@require_POST
def approve_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, status=Ticket.Status.PENDING_APPROVAL)
    if request.user.role != User.Role.APPROVER: return HttpResponse(status=403)
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
    if request.user.role != User.Role.APPROVER: return HttpResponse(status=403)
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

# ==========================================================================
# ATTACHMENT DOWNLOAD
# ==========================================================================

@login_required
def attachment_download(request, pk):
    """
    Serves a file attachment. Only the ticket requester or agents/leads/admins can download.
    """
    attachment = get_object_or_404(Attachment, pk=pk)
    ticket = attachment.ticket
    if request.user != ticket.requester and request.user.role not in ['AGENT', 'TEAM_LEAD', 'ADMIN', 'SUPERADMIN']:
        raise PermissionDenied
    response = FileResponse(attachment.file.open('rb'), content_type=attachment.content_type or 'application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{attachment.filename}"'
    return response

# ==========================================================================
# SLA MANAGEMENT (Admin & Superadmin only)
# ==========================================================================

def is_admin(user): return user.role in ['ADMIN', 'SUPERADMIN']

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