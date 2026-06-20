from django.urls import path
from django.contrib.auth import views as auth_views
# from apps.accounts.forms import EmailAuthenticationForm
from .views import CustomLoginView
from . import views
from .views.admin_users import (
    admin_user_list, admin_user_create, admin_user_edit, admin_user_toggle_active, admin_user_change_password
)

app_name = 'accounts'

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('validate-email/', views.validate_email_ajax, name='validate_email'),
    path('validate-password/', views.validate_password_ajax, name='validate_password'),
    path('register/', views.register, name='register'),
    path('verify/<uidb64>/<token>/', views.verify_email, name='verify_email'),
    # ---- Password Reset ----
    path('password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='registration/password_reset.html',
            email_template_name='registration/password_reset_email.html',
            subject_template_name='registration/password_reset_subject.txt',
            success_url='/accounts/password-reset/done/'
        ),
        name='password_reset'),
    path('password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html'
        ),
        name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html',
            success_url='/accounts/password-reset-complete/'
        ),
        name='password_reset_confirm'),
    path('password-reset-complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html'
        ),
        name='password_reset_complete'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),
    path('profile/', views.profile, name='profile'),
    path('admin/users/', admin_user_list, name='admin_users'),
    path('admin/users/create/', admin_user_create, name='admin_user_create'),
    path('admin/users/<int:pk>/edit/', admin_user_edit, name='admin_user_edit'),
    path('admin/users/<int:pk>/toggle-active/', admin_user_toggle_active, name='admin_user_toggle_active'),
    path('admin/users/<int:pk>/change-password/', admin_user_change_password, name='admin_user_change_password'),
]