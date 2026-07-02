from django.contrib import admin
from .models import Ticket, TicketComment, Attachment, TicketActivityLog, Macro, RemoteConnector, Asset, RemoteSession

class CommentInline(admin.TabularInline):
    model = TicketComment
    extra = 0

class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['number', 'title', 'requester', 'assigned_to', 'status', 'priority', 'created_at']
    list_filter = ['status', 'priority', 'type', 'impact', 'urgency']
    search_fields = ['number', 'title', 'description', 'requester__username']
    readonly_fields = ['number', 'priority']  # auto-generated
    inlines = [CommentInline, AttachmentInline]

@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'author', 'visibility', 'created_at']

@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'filename', 'uploaded_by', 'uploaded_at']

@admin.register(TicketActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'action', 'actor', 'created_at']
    # Make it read-only to preserve append-only nature
    readonly_fields = ['ticket', 'action', 'actor', 'details', 'correlation_id', 'created_at']
    def has_add_permission(self, request):
        return False  # only created programmatically
    

@admin.register(Macro)
class MacroAdmin(admin.ModelAdmin):
    list_display = ['title', 'visibility', 'created_by', 'created_at']


@admin.register(RemoteConnector)
class RemoteConnectorAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ['tracking_id', 'name', 'asset_type', 'serial_number', 'assigned_to', 'status', 'location']
    list_filter = ['asset_type', 'status', 'location']
    search_fields = ['tracking_id', 'name', 'serial_number', 'model', 'manufacturer']
    readonly_fields = ['tracking_id', 'created_at', 'updated_at']

@admin.register(RemoteSession)
class RemoteSessionAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'requester', 'agent', 'connector', 'status', 'created_at']
    list_filter = ['status', 'connector']
    readonly_fields = ['created_at', 'updated_at', 'started_at', 'ended_at']