from django import forms
from .models import Ticket, TicketComment, Asset
from apps.common.models import Category
from django.utils.text import slugify


class TicketForm(forms.ModelForm):
    # Override category field to handle "OTHER"
    category = forms.CharField(
        required=True,
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-lg border py-2.5 px-4 text-sm transition focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary',
            'hx-get': '',
            'hx-target': '#kb-suggestions',
            'hx-trigger': 'change',
        })
    )

    # Custom field for "Other" category
    category_other = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'block w-full rounded-lg border py-2.5 px-4 text-sm transition focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary',
            'placeholder': 'Enter custom category...',
            'id': 'category_other'
        }),
        label='Custom Category'
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate the select choices
        categories = Category.objects.all().values_list('id', 'name')
        self.fields['category'].widget.choices = [('', '-- Select Category --')] + list(categories) + [('OTHER', '+ Add Custom Category')]
        
        # If editing and category is custom (not in choices), set to OTHER and pre-fill category_other
        instance = kwargs.get('instance')
        if instance and instance.category_id:
            category_ids = [c[0] for c in categories]
            if instance.category_id not in category_ids:
                self.fields['category'].initial = 'OTHER'
                self.initial['category_other'] = instance.category.name

    def clean(self):
        cleaned_data = super().clean()
        
        # Handle "OTHER" for category
        category = cleaned_data.get('category')
        category_other = cleaned_data.get('category_other', '').strip()
        
        if category == 'OTHER':
            if category_other:
                # Try to find existing category or create new one
                category_obj, created = Category.objects.get_or_create(
                    name=category_other,
                    defaults={'slug': slugify(category_other)}
                )
                cleaned_data['category'] = category_obj
            else:
                self.add_error('category_other', 'Please enter a custom category.')
        elif category and category != '':
            try:
                # Ensure category is a Category object
                if isinstance(category, str):
                    category_obj = Category.objects.get(pk=category)
                    cleaned_data['category'] = category_obj
            except (Category.DoesNotExist, ValueError):
                self.add_error('category', 'Please select a valid category.')
        
        return cleaned_data


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
    # Override the fields completely to bypass model choices validation
    asset_type = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full rounded-lg border py-2 px-3 text-sm focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary'
        })
    )
    
    location = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full rounded-lg border py-2 px-3 text-sm focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary'
        })
    )
    
    status = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full rounded-lg border py-2 px-3 text-sm focus:outline-none focus:ring-2 bg-background border-border text-text-primary ring-primary'
        })
    )
    
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate the select choices
        self.fields['asset_type'].widget.choices = [('', '-- Select Type --')] + list(Asset.AssetType.choices)
        self.fields['location'].widget.choices = [('', '-- Select Location --')] + list(Asset.Location.choices)
        self.fields['status'].widget.choices = [('', '-- Select Status --')] + list(Asset.Status.choices)

    def clean(self):
        cleaned_data = super().clean()
        
        # --- Handle "OTHER" for asset_type ---
        asset_type = cleaned_data.get('asset_type')
        asset_type_other = cleaned_data.get('asset_type_other', '').strip()
        
        if asset_type == 'OTHER':
            if asset_type_other:
                cleaned_data['asset_type'] = asset_type_other
            else:
                self.add_error('asset_type_other', 'Please enter a custom asset type.')
        elif not asset_type:
            self.add_error('asset_type', 'Asset type is required.')
        
        # --- Handle "OTHER" for location ---
        location = cleaned_data.get('location')
        location_other = cleaned_data.get('location_other', '').strip()
        
        if location == 'OTHER':
            if location_other:
                cleaned_data['location'] = location_other
            else:
                self.add_error('location_other', 'Please enter a custom location.')
        elif not location:
            cleaned_data['location'] = ''
        
        # --- Handle "OTHER" for status ---
        status = cleaned_data.get('status')
        status_other = cleaned_data.get('status_other', '').strip()
        
        if status == 'OTHER':
            if status_other:
                cleaned_data['status'] = status_other
            else:
                self.add_error('status_other', 'Please enter a custom status.')
        elif not status:
            cleaned_data['status'] = 'ACTIVE'
        
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
            'warranty_duration_years': forms.Select(attrs={
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