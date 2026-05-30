from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .forms import RegistrationForm, ProfileForm
from .models import User
from apps.tickets.models import Ticket

@login_required
def dashboard(request):
    role = request.user.role
    template_map = {
        'END_USER': 'dashboards/end_user_dashboard.html',
        'AGENT': 'dashboards/agent_dashboard.html',
        'TEAM_LEAD': 'dashboards/team_lead_dashboard.html',
        'APPROVER': 'dashboards/approver_dashboard.html',
        'ADMIN': 'dashboards/admin_dashboard.html',
        'SUPERADMIN': 'dashboards/super_admin_dashboard.html',   # same for now
    }
    template = template_map.get(role, 'dashboard/generic_dashboard.html')
    context = {}
    if role == 'END_USER':
        context['open_tickets_count'] = Ticket.objects.filter(
            requester=request.user, status__in=['NEW', 'TRIAGED', 'ASSIGNED', 'IN_PROGRESS', 'PENDING_USER', 'PENDING_VENDOR']
        ).count()
        context['recent_tickets'] = Ticket.objects.filter(requester=request.user).order_by('-created_at')[:3]
    elif role == 'AGENT':
        # All non-closed/resolved tickets (open in the system)
        open_statuses = ['NEW', 'TRIAGED', 'ASSIGNED', 'IN_PROGRESS', 'PENDING_USER', 'PENDING_VENDOR']
        context['total_open_tickets'] = Ticket.objects.filter(status__in=open_statuses).count()
        context['my_open_tickets'] = Ticket.objects.filter(
            assigned_to=request.user,
            status__in=open_statuses
        ).count()
        # Unassigned queue count
        context['unassigned_count'] = Ticket.objects.filter(
            assigned_to__isnull=True
        ).exclude(status__in=['RESOLVED', 'CLOSED']).count()
        # Recent unassigned tickets (top 3)
        context['recent_unassigned'] = Ticket.objects.filter(
            assigned_to__isnull=True
        ).exclude(status__in=['RESOLVED', 'CLOSED']).order_by('-created_at')[:3]
        # Placeholder for future SLA data
        context['sla_breaches'] = 0
        context['avg_response_time'] = None   # you can compute later
        
    return render(request, template, context)

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Send verification email
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            verification_link = request.build_absolute_uri(
                f'/accounts/verify/{uid}/{token}/'
            )
            subject = "Verify your email address"
            html_message = render_to_string('registration/verification_email.html', {
                'user': user,
                'link': verification_link,
            })
            # For development, print to console; replace with real email backend later
            print(f"Verification link: {verification_link}")
            user.email_user(subject, '', html_message=html_message)
            return render(request, 'registration/register_done.html')
    else:
        form = RegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return render(request, 'registration/verify_email_done.html')
    else:
        return render(request, 'registration/verify_email_failed.html')

@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)

    # Choose sidebar based on role
    sidebar_map = {
        'END_USER': 'partials/sidebar_end_user.html',
        'AGENT': 'partials/sidebar_agent.html',      # will be replaced later
        'TEAM_LEAD': 'partials/sidebar_generic.html',
        'APPROVER': 'partials/sidebar_generic.html',
        'ADMIN': 'partials/sidebar_generic.html',
        'SUPERADMIN': 'partials/sidebar_superadmin.html',
    }
    sidebar_template = sidebar_map.get(request.user.role, 'partials/sidebar_generic.html')

    return render(request, 'dashboards/profile.html', {
        'form': form,
        'sidebar_template': sidebar_template,
    })