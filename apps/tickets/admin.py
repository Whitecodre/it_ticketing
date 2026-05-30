from django.contrib import admin
from .models import Ticket, TicketComment, Attachment, TicketActivityLog, Macro

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