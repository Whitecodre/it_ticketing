import logging
from django.contrib import messages
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.views import LoginView
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import strip_tags
from django.db.models import F, DurationField, ExpressionWrapper, Count, Q
from datetime import timedelta
from ..forms import ProfileForm, EmailAuthenticationForm, RegistrationStep1Form, RegistrationStep2Form, ChangePasswordForm, UserSettingsForm
from ..models import User, UserProfile
from ..utils import validate_password_strength
from apps.tickets.models import Ticket, TicketActivityLog, SLA, BusinessCalendar, EscalationRule


User = get_user_model()
logger = logging.getLogger(__name__)


class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        remember_me = self.request.POST.get('remember_me')
        if remember_me:
            self.request.session.set_expiry(30 * 24 * 60 * 60)
        else:
            self.request.session.set_expiry(0)
        return super().form_valid(form)

    def form_invalid(self, form):
        # Pass the submitted username back to the template
        return self.render_to_response(
            self.get_context_data(
                form=form,
                username=form.data.get('username', '')
            )
        )

def validate_email_ajax(request):
    email = request.GET.get('email', '').strip()
    if not email:
        return render(request, 'partials/email_validation.html', {
            'valid': False,
            'message': 'Email is required.'
        })
    if User.objects.filter(email=email).exists():
        return render(request, 'partials/email_validation.html', {
            'valid': False,
            'message': 'This email is already registered.'
        })
    return render(request, 'partials/email_validation.html', {
        'valid': True,
        'message': 'Email is available.'
    })

def validate_password_ajax(request):
    password = request.GET.get('password') or request.GET.get('password1', '')
    if not password:
        return HttpResponse('')
    result = validate_password_strength(password)
    try:
        from django.contrib.auth.password_validation import validate_password
        validate_password(password)
        result['valid'] = True
    except Exception:
        result['valid'] = False
    return render(request, 'partials/password_strength.html', result)

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
        open_statuses = ['NEW', 'TRIAGED', 'ASSIGNED', 'IN_PROGRESS', 'PENDING_USER', 'PENDING_VENDOR']
        
        # Total open tickets (system wide)
        context['total_open_tickets'] = Ticket.objects.filter(status__in=open_statuses).count()
        
        # My open tickets
        context['my_open_tickets'] = Ticket.objects.filter(
            assigned_to=request.user,
            status__in=open_statuses
        ).count()
        
        # Unassigned queue count
        context['unassigned_count'] = Ticket.objects.filter(
            assigned_to__isnull=True
        ).exclude(status__in=['RESOLVED', 'CLOSED', 'PENDING_APPROVAL']).count()
        
        # Recent unassigned (5)
        context['recent_unassigned'] = Ticket.objects.filter(
            assigned_to__isnull=True
        ).exclude(status__in=['RESOLVED', 'CLOSED', 'PENDING_APPROVAL']).order_by('-created_at')[:5]
        
        # Recent assigned to me (5)
        context['assigned_to_me_tickets'] = Ticket.objects.filter(
            assigned_to=request.user
        ).exclude(status__in=['RESOLVED', 'CLOSED']).order_by('-created_at')[:5]
        
        # ---- KPI: Total Solved, Good, Bad ----
        resolved = Ticket.objects.filter(assigned_to=request.user, status__in=['RESOLVED', 'CLOSED'])
        total_solved = resolved.count()
        context['total_solved'] = total_solved
        
        good = 0
        bad = 0
        for ticket in resolved:
            try:
                sla = SLA.objects.get(priority=ticket.priority)
                if ticket.resolved_at and (ticket.resolved_at - ticket.created_at).total_seconds() / 60 <= sla.resolution_minutes:
                    good += 1
                else:
                    bad += 1
            except SLA.DoesNotExist:
                # If no SLA defined, treat as good (or ignore)
                good += 1
        context['good_tickets'] = good
        context['bad_tickets'] = bad
        
        # Placeholders
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
        pending_count = Ticket.objects.filter(status='PENDING_APPROVAL').count()
        overdue_count = Ticket.objects.filter(
            status='PENDING_APPROVAL', created_at__lt=timezone.now() - timedelta(days=2)
        ).count()
        pending_tickets = Ticket.objects.filter(status='PENDING_APPROVAL').order_by('-created_at')[:10]
        recent_logs = TicketActivityLog.objects.filter(
            actor=request.user, action__in=['approved', 'rejected']
        ).select_related('ticket').order_by('-created_at')[:5]

        # --- New KPIs ---
        # Total approved this month
        this_month = timezone.now().month
        approved_this_month = TicketActivityLog.objects.filter(
            actor=request.user,
            action='approved',
            created_at__month=this_month
        ).count()

        # Approval rate (this month: approved / (approved + rejected))
        total_decisions = TicketActivityLog.objects.filter(
            actor=request.user,
            action__in=['approved', 'rejected'],
            created_at__month=this_month
        ).count()
        approval_rate = round((approved_this_month / total_decisions * 100), 1) if total_decisions > 0 else 0

        context = {
            'pending_count': pending_count,
            'overdue_count': overdue_count,
            'pending_tickets': pending_tickets,
            'recent_logs': recent_logs,
            'approved_this_month': approved_this_month,
            'approval_rate': approval_rate,
            'sidebar_template': get_sidebar_template(request.user),
        }
        
    return render(request, template, context)

def register(request):
    step = request.GET.get('step', '1')
    
    if request.method == 'POST':
        if step == '1':
            form = RegistrationStep1Form(request.POST)
            if form.is_valid():
                # Explicitly lowercase email
                email = form.cleaned_data['email'].lower()
                request.session['registration_data'] = {
                    'first_name': form.cleaned_data['first_name'],
                    'last_name': form.cleaned_data['last_name'],
                    'email': form.cleaned_data['email'],
                    'department': form.cleaned_data['department'],
                }
                return redirect(reverse('accounts:register') + '?step=2')
            else:
                return render(request, 'registration/register_step1.html', {'form': form})
        else:
            data = request.session.get('registration_data')
            if not data:
                return redirect('accounts:register')
            form = RegistrationStep2Form(request.POST)
            if form.is_valid():
                email = data.get('email', '').lower()   # extra safety
                user = User.objects.create_user(
                    email=email,
                    password=form.cleaned_data['password1'],
                    first_name=data.get('first_name'),
                    last_name=data.get('last_name'),
                    department=data.get('department'),
                    is_active=False,
                    email_verified=False
                )
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

                request.session.pop('registration_data', None)
                return render(request, 'registration/register_done.html', {
                    'email_error': email_error,
                    'user_email': user.email,
                    'user_id': user.pk,
                })
            else:
                return render(request, 'registration/register_step2.html', {'form': form})
    
    # GET request – show current step
    if step == '1':
        # Pre‑fill with session data if it exists
        initial = request.session.get('registration_data', {})
        form = RegistrationStep1Form(initial=initial)
        return render(request, 'registration/register_step1.html', {'form': form})
    else:
        if not request.session.get('registration_data'):
            return redirect('accounts:register')
        return render(request, 'registration/register_step2.html', {'form': RegistrationStep2Form()})

def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.email_verified = True
        user.save()
        return render(request, 'registration/verify_email_done.html')
    else:
        return render(request, 'registration/verify_email_failed.html')

def resend_verification(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if not email:
            message = "Please enter your email address."
            success = False
            return render(request, 'registration/resend_verification_done.html', {
                'message': message,
                'success': success,
            })
        try:
            user = User.objects.get(email__iexact=email, is_active=False)
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
    # Ensure profile exists
    if not hasattr(request.user, 'profile'):
        UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
        if 'save_profile' in request.POST:
            form = ProfileForm(request.POST, request.FILES, instance=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profile updated successfully.')
                return redirect('accounts:profile')
        elif 'save_settings' in request.POST:
            settings_form = UserSettingsForm(request.POST, instance=request.user.profile)
            if settings_form.is_valid():
                settings_form.save()
                messages.success(request, 'Settings updated successfully.')
                return redirect('accounts:profile')
        elif 'change_password' in request.POST:
            password_form = ChangePasswordForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password changed successfully.')
                return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)
        settings_form = UserSettingsForm(instance=request.user.profile)
        password_form = ChangePasswordForm(request.user)

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
        'settings_form': settings_form,
        'password_form': password_form,
        'sidebar_template': sidebar_template,
    })