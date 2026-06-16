import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.views import LoginView
from django.utils import timezone
from django.utils.html import strip_tags
from django.db.models import F, DurationField, ExpressionWrapper, Count, Q
from datetime import timedelta
from ..forms import RegistrationForm, ProfileForm, EmailAuthenticationForm
from ..models import User
from apps.tickets.models import Ticket, TicketActivityLog, SLA, BusinessCalendar, EscalationRule, TicketActivityLog

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        remember_me = self.request.POST.get('remember_me')
        if remember_me:
            # Set session to expire in 30 days (or whatever you prefer)
            self.request.session.set_expiry(30 * 24 * 60 * 60)  # 30 days in seconds
        else:
            # Session expires when the browser closes
            self.request.session.set_expiry(0)
        return super().form_valid(form)

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
            requester=request.user,
            status__in=['NEW', 'TRIAGED', 'ASSIGNED', 'IN_PROGRESS', 'PENDING_USER', 'PENDING_VENDOR']
        ).count()
        context['recent_tickets'] = Ticket.objects.filter(requester=request.user).order_by('-created_at')[:5]
        # Status counts for the mini stats bar
        context['all_count'] = Ticket.objects.filter(requester=request.user).count()
        context['open_count'] = Ticket.objects.filter(requester=request.user, status='NEW').count()
        context['in_progress_count'] = Ticket.objects.filter(requester=request.user, status='IN_PROGRESS').count()
        context['resolved_count'] = Ticket.objects.filter(requester=request.user, status='RESOLVED').count()
        context['closed_count'] = Ticket.objects.filter(requester=request.user, status='CLOSED').count()
    elif role == 'AGENT':
        # All non-closed/resolved tickets (open in the system)
        open_statuses = ['NEW', 'TRIAGED', 'ASSIGNED', 'IN_PROGRESS', 'PENDING_USER', 'PENDING_VENDOR']
        context['total_open_tickets'] = Ticket.objects.filter(status__in=open_statuses).count()
        context['my_open_tickets'] = Ticket.objects.filter(
            assigned_to=request.user,
            status__in=open_statuses
        ).count()
        # Unassigned queue count (excluding pending approval)
        context['unassigned_count'] = Ticket.objects.filter(
            assigned_to__isnull=True
        ).exclude(status__in=['RESOLVED', 'CLOSED', 'PENDING_APPROVAL']).count()

        # Recent unassigned tickets (top 3, excluding pending approval)
        context['recent_unassigned'] = Ticket.objects.filter(
            assigned_to__isnull=True
        ).exclude(status__in=['RESOLVED', 'CLOSED', 'PENDING_APPROVAL']).order_by('-created_at')[:3]
        # Placeholder for future SLA data
        context['sla_breaches'] = 0
        context['avg_response_time'] = None   # you can compute later
    elif role in ['ADMIN', 'SUPERADMIN']:
        # KPI: Total tickets this month
        context['total_tickets_month'] = Ticket.objects.filter(created_at__month=timezone.now().month).count()

        # SLA Compliance calculation
        resolved_tickets = Ticket.objects.filter(status__in=['RESOLVED', 'CLOSED'], resolved_at__isnull=False)
        compliant = 0
        total = 0
        for ticket in resolved_tickets:
            try:
                sla = SLA.objects.get(priority=ticket.priority)
                resolution_time = ticket.resolved_at - ticket.created_at
                if resolution_time.total_seconds() / 60 <= sla.resolution_minutes:
                    compliant += 1
            except SLA.DoesNotExist:
                # If no SLA defined, consider as compliant? We'll skip.
                pass
            total += 1
        context['sla_compliance'] = round((compliant / total * 100), 1) if total > 0 else 100.0

        # Active connectors placeholder
        context['active_connectors'] = 5   # static for now

        # SLA policies summary
        context['slas'] = SLA.objects.all().order_by('priority')
        context['escalation_rules'] = EscalationRule.objects.all().order_by('priority', 'timer_type', 'threshold_percent')
        context['calendars'] = BusinessCalendar.objects.all()

        # Recent audit logs
        context['recent_audit_logs'] = TicketActivityLog.objects.select_related('ticket', 'actor').order_by('-created_at')[:5]

        # RBAC matrix (dynamic from user roles)
        context['role_choices'] = User.Role.choices
    elif role == 'TEAM_LEAD':
        open_statuses = ['NEW', 'TRIAGED', 'ASSIGNED', 'IN_PROGRESS', 'PENDING_USER', 'PENDING_VENDOR']
        team_members = User.objects.filter(department=request.user.department, role='AGENT')
        context['team_open_tickets'] = Ticket.objects.filter(
            status__in=open_statuses,
            assigned_to__in=team_members
        ).count()
        context['unassigned_count'] = Ticket.objects.filter(
            assigned_to__isnull=True
        ).exclude(status__in=['RESOLVED', 'CLOSED']).count()
        context['sla_breaches'] = 0          # placeholder
        context['team_members'] = team_members
        context['recent_team_tickets'] = Ticket.objects.filter(
            assigned_to__in=team_members
        ).exclude(status__in=['RESOLVED', 'CLOSED']).order_by('-created_at')[:5]
    elif role == 'APPROVER':
        context['pending_count'] = Ticket.objects.filter(status='PENDING_APPROVAL').count()
        context['overdue_count'] = Ticket.objects.filter(
            status='PENDING_APPROVAL', created_at__lt=timezone.now() - timedelta(days=2)
        ).count()
        context['pending_tickets'] = Ticket.objects.filter(status='PENDING_APPROVAL').order_by('-created_at')[:10]
        context['recent_logs'] = TicketActivityLog.objects.filter(
            actor=request.user, action__in=['approved', 'rejected']
        ).select_related('ticket').order_by('-created_at')[:5]
        
    return render(request, template, context)

logger = logging.getLogger(__name__)

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
            plain_message = strip_tags(html_message)
            email_error = False
            try:
                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=html_message,
                    fail_silently=False,
                )
            except Exception as e:
                logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
                email_error = True

            return render(request, 'registration/register_done.html', {
                'email_error': email_error,
                'user_email': user.email,
                'user_id': user.pk,
            })
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

def resend_verification(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email, is_active=False)
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
            plain_message = strip_tags(html_message)
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            message = "Verification email sent. Please check your inbox."
            success = True
        except User.DoesNotExist:
            message = "No inactive user found with that email."
            success = False
        except Exception as e:
            logger.error(f"Resend verification error: {str(e)}")
            message = f"Failed to send email: {str(e)}"
            success = False
        return render(request, 'registration/resend_verification_done.html', {
            'message': message,
            'success': success,
        })
    return render(request, 'registration/resend_verification.html')

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
        'AGENT': 'partials/sidebar_agent.html',
        'TEAM_LEAD': 'partials/sidebar_team_lead.html',
        'APPROVER': 'partials/sidebar_approver.html',
        'ADMIN': 'partials/sidebar_admin.html',
        'SUPERADMIN': 'partials/sidebar_superadmin.html',
    }
    sidebar_template = sidebar_map.get(request.user.role, 'partials/sidebar_generic.html')

    return render(request, 'dashboards/profile.html', {
        'form': form,
        'sidebar_template': sidebar_template,
    })