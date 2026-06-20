from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.utils.safestring import mark_safe
from django.urls import reverse
from .models import User

class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'autofocus': True, 'placeholder': 'Email address'})
    )
    error_messages = {
        'invalid_login': 'Please enter a correct email and password. Note that both fields may be case‑sensitive.',
        'inactive_unverified': mark_safe(
            'Your email address has not been verified. Please check your inbox for the verification link, or <a href="{resend_link}" class="text-primary underline">request a new verification email</a>.'
        ),
        'inactive_by_admin': 'Your account has been deactivated by an administrator. Please contact support to reactivate it.',
    }

    # def clean_username(self):
    #     username = self.cleaned_data.get('username')
    #     if username:
    #         username = username.lower()
    #     return username

    def clean(self):
        cleaned_data = super().clean()
        # Optional debug:
        # print("User found:", self.user_cache)
        return cleaned_data

    def confirm_login_allowed(self, user):
        if not user.is_active:
            if hasattr(user, 'email_verified') and not user.email_verified:
                resend_link = reverse('accounts:resend_verification')
                msg = self.error_messages['inactive_unverified'].format(resend_link=resend_link)
                raise ValidationError(msg, code='inactive_unverified')
            else:
                raise ValidationError(
                    self.error_messages['inactive_by_admin'],
                    code='inactive_by_admin'
                )

class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    department = forms.ChoiceField(choices=User.DEPARTMENT_CHOICES, required=True)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'department', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        # Let Django’s built‑in validators check common passwords, length, etc.
        validate_password(password)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.department = self.cleaned_data['department']
        user.role = User.Role.END_USER
        user.is_active = False
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'department', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'block w-full rounded-lg border py-2.5 px-4 text-sm transition focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'block w-full rounded-lg border py-2.5 px-4 text-sm transition focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary',
                'placeholder': 'Last Name'
            }),
            'department': forms.Select(attrs={
                'class': 'block w-full rounded-lg border py-2.5 px-4 text-sm transition focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary'
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'block w-full text-sm text-text-secondary file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-white hover:file:bg-primary-light'
            }),
        }

class RegistrationStep1Form(forms.Form):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    department = forms.ChoiceField(choices=User.DEPARTMENT_CHOICES, required=True)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower()   # <-- critical
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

class RegistrationStep2Form(forms.Form):
    password1 = forms.CharField(widget=forms.PasswordInput, min_length=8)
    password2 = forms.CharField(widget=forms.PasswordInput, min_length=8)

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords do not match.")
        return cleaned_data