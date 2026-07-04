from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Custom manager where email is the unique identifier instead of username."""

    def _create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        email = email.lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.SUPERADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None

    email = models.EmailField(_('email address'), unique=True)

    class Role(models.TextChoices):
        SUPERADMIN = 'SUPERADMIN', _('Super Admin')
        ADMIN = 'ADMIN', _('Admin')
        TEAM_LEAD = 'TEAM_LEAD', _('Team Lead')
        # APPROVER = 'APPROVER', _('Approver')  # <-- REMOVED
        AGENT = 'AGENT', _('Support Team')
        END_USER = 'END_USER', _('User')

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.END_USER,
    )

    DEPARTMENT_CHOICES = [
        ('MARINE', 'Marine'),
        ('IT', 'IT'),
        ('ACCOUNTING', 'Accounting'),
        ('LEGAL', 'Legal'),
        ('QHSE', 'QHSE'),
        ('OPERATIONS', 'Operations'),
        ('PROJECT', 'Project'),
        ('VESSEL_CATERING', 'Vessel Catering'),
        ('PURCHASE_PROTOCOL', 'Purchase/Protocol'),
        ('FREIGHT', 'Freight'),
        ('STORE', 'Store'),
        ('HR', 'HR'),
        ('ADMIN', 'Admin'),
        ('COMMERCIAL', 'Commercial'),
    ]
    department = models.CharField(
        max_length=30,
        choices=DEPARTMENT_CHOICES,
        blank=False,
    )

    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    email_verified = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_users'
    )

    def get_full_name_with_role(self):
        """Returns full name with role in parentheses, e.g. 'John Doe (Agent)'"""
        name = self.get_full_name() or self.email
        return f"{name} ({self.get_role_display()})"

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'department']

    def save(self, *args, **kwargs):
        # Delete the old avatar file if a new one is being uploaded
        if self.pk:
            try:
                old = User.objects.get(pk=self.pk)
                if old.avatar and old.avatar != self.avatar:
                    old.avatar.delete(save=False)
            except User.DoesNotExist:
                pass

        # Auto-set staff / superuser based on role
        if self.role in [self.Role.SUPERADMIN, self.Role.ADMIN, self.Role.TEAM_LEAD,
                         self.Role.AGENT]:  # Removed APPROVER
            self.is_staff = True
        else:
            self.is_staff = False
        self.is_superuser = (self.role == self.Role.SUPERADMIN)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    timezone = models.CharField(max_length=50, default='UTC')

    LANGUAGE_CHOICES = [
        ('en', _('English')),
        ('fr', _('French')),
        ('es', _('Spanish')),
        ('de', _('German')),
    ]
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    
    DEFAULT_VIEW_CHOICES = [
        ('list', _('List')),
        ('kanban', _('Kanban')),
    ]
    default_ticket_view = models.CharField(max_length=20, choices=DEFAULT_VIEW_CHOICES, default='list')
    
    email_notifications = models.BooleanField(default=True, help_text=_('Receive email notifications for ticket updates'))
    in_app_notifications = models.BooleanField(default=True, help_text=_('Receive in-app notifications (bell icon)'))
    
    ticket_signature = models.TextField(blank=True, help_text=_('Default signature for ticket replies (plain text)'))

    def __str__(self):
        return self.user.email