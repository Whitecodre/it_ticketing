from django import forms
from .models import Ticket, TicketComment
from apps.common.models import Category

class TicketForm(forms.ModelForm):
    # Explicit field override to remove the blank option
    category = forms.ModelChoiceField(
    queryset=Category.objects.all(),
    empty_label="Select a category",   # ← friendly placeholder
    required=False,
    widget=forms.Select(attrs={
        'class': 'block w-full rounded-lg border py-2.5 px-4 text-sm transition focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary',
        'hx-get': '',
        'hx-target': '#kb-suggestions',
        'hx-trigger': 'change',
    }),
)

    class Meta:
        model = Ticket
        fields = ['type', 'title', 'description', 'category', 'impact', 'urgency']
        widgets = {
            'type': forms.Select(attrs={
                'class': 'block w-full rounded-lg border py-2.5 px-4 text-sm transition focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary'
            }),
            'title': forms.TextInput(attrs={
                'class': 'block w-full rounded-lg border py-2.5 px-4 text-sm transition focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary',
                'placeholder': 'Brief summary of the issue'
            }),
            'description': forms.Textarea(attrs={
                'class': 'block w-full rounded-lg border py-2.5 px-4 text-sm transition focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary',
                'rows': 5,
                'placeholder': 'Describe your issue or request in detail'
            }),
            'impact': forms.Select(attrs={
                'class': 'block w-full rounded-lg border py-2.5 px-4 text-sm transition focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary'
            }),
            'urgency': forms.Select(attrs={
                'class': 'block w-full rounded-lg border py-2.5 px-4 text-sm transition focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary'
            }),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = TicketComment
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={
                'rows': 3,
                'class': 'block w-full rounded-lg border py-2.5 px-4 text-sm transition focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary',
                'placeholder': 'Add a comment or provide more information...'
            }),
        }