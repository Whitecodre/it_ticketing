from django import forms
from .models import Ticket, TicketComment, Asset
from apps.common.models import Category

class TicketForm(forms.ModelForm):
    # Explicit field override to remove the blank option
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        empty_label=None, 
        required=True,
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

class AssetForm(forms.ModelForm):
    # Custom field for "Other" location
    location_other = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full rounded-lg border py-2 px-3 text-sm focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary',
            'placeholder': 'Enter custom location...',
            'id': 'location_other'
        }),
        label='Custom Location'
    )
    
    # Custom field for "Other" asset type
    asset_type_other = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full rounded-lg border py-2 px-3 text-sm focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary',
            'placeholder': 'Enter custom asset type...',
            'id': 'asset_type_other'
        }),
        label='Custom Asset Type'
    )
    
    # Custom field for "Other" status
    status_other = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full rounded-lg border py-2 px-3 text-sm focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary',
            'placeholder': 'Enter custom status...',
            'id': 'status_other'
        }),
        label='Custom Status'
    )

    def clean(self):
        cleaned_data = super().clean()
        
        # Handle "Other" for asset_type
        asset_type = cleaned_data.get('asset_type')
        asset_type_other = cleaned_data.get('asset_type_other')
        if asset_type == 'OTHER' and asset_type_other:
            cleaned_data['asset_type'] = asset_type_other
        
        # Handle "Other" for status
        status = cleaned_data.get('status')
        status_other = cleaned_data.get('status_other')
        if status == 'OTHER' and status_other:
            cleaned_data['status'] = status_other
        
        # Handle "Other" for location
        location = cleaned_data.get('location')
        location_other = cleaned_data.get('location_other')
        if location == 'OTHER' and location_other:
            cleaned_data['location'] = location_other
        
        return cleaned_data

    class Meta:
        model = Asset
        fields = [
            'name', 'asset_type', 'status', 'serial_number', 'model', 
            'manufacturer', 'location', 'purchase_date', 'warranty_duration_years',
            'warranty_expiry', 'assigned_to', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border py-2 px-3 text-sm focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary'
            }),
            'serial_number': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border py-2 px-3 text-sm focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary'
            }),
            'model': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border py-2 px-3 text-sm focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary'
            }),
            'manufacturer': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border py-2 px-3 text-sm focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary'
            }),
            'purchase_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full rounded-lg border py-2 px-3 text-sm focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary'
            }),
            'warranty_expiry': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full rounded-lg border py-2 px-3 text-sm bg-gray-100 text-gray-600 cursor-not-allowed focus:outline-none',
                'readonly': True
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'w-full rounded-lg border py-2 px-3 text-sm focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full rounded-lg border py-2 px-3 text-sm focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary'
            }),
        }