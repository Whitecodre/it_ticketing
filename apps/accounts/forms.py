from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User
from django.contrib.auth.forms import AuthenticationForm


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
            raise forms.ValidationError("A user with this email already exists.")
        return email

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
    

class EmailAuthenticationForm(AuthenticationForm):
    # This overrides the default 'username' field to use 'email'
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'autofocus': True})
    )

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