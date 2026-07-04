import datetime
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.accounts.models import User

class Ticket(models.Model):
    class Type(models.TextChoices):
        INCIDENT = 'INCIDENT', 'Incident'
        SERVICE_REQUEST = 'SERVICE_REQUEST', 'Service Request'
    
    def sla_status(self):
        now = timezone.now()
        result = {'response': 'ok', 'resolution': 'ok', 'response_pct': 0, 'resolution_pct': 0}

        try:
            sla = SLA.objects.get(priority=self.priority)
        except SLA.DoesNotExist:
            return result  # no policy → always ok

        # Response
        if self.response_due_at:
            total_secs = (self.response_due_at - self.created_at).total_seconds()
        else:
            total_secs = sla.response_minutes * 60   # fallback: use SLA target
        if total_secs > 0:
            elapsed_secs = (now - self.created_at).total_seconds()
            pct = min(100, (elapsed_secs / total_secs) * 100)
            result['response_pct'] = round(pct, 1)
            if pct >= 100:
                result['response'] = 'breached'
            elif pct >= 75:
                result['response'] = 'warning'

        # Resolution
        if self.resolution_due_at:
            total_secs = (self.resolution_due_at - self.created_at).total_seconds()
        else:
            total_secs = sla.resolution_minutes * 60
        if total_secs > 0:
            elapsed_secs = (now - self.created_at).total_seconds()
            pct = min(100, (elapsed_secs / total_secs) * 100)
            result['resolution_pct'] = round(pct, 1)
            if pct >= 100:
                result['resolution'] = 'breached'
            elif pct >= 75:
                result['resolution'] = 'warning'

        # Overall status
        if result['response'] == 'breached' or result['resolution'] == 'breached':
            result['overall'] = 'breached'
        elif result['response'] == 'warning' or result['resolution'] == 'warning':
            result['overall'] = 'warning'
        else:
            result['overall'] = 'ok'
        return result

    class Status(models.TextChoices):
        NEW = 'NEW', 'New'
        TRIAGED = 'TRIAGED', 'Triaged'
        ASSIGNED = 'ASSIGNED', 'Assigned'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        PENDING_USER = 'PENDING_USER', 'Pending User'
        PENDING_VENDOR = 'PENDING_VENDOR', 'Pending Vendor'
        PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending Approval'
        PENDING_MANAGER_REVIEW = 'PENDING_MANAGER_REVIEW', 'Pending Manager Review'
        PENDING_FULFILLMENT = 'PENDING_FULFILLMENT', 'Pending Fulfillment'  # NEW
        APPROVED = 'APPROVED', 'Approved'
        RESOLVED = 'RESOLVED', 'Resolved'
        CLOSED = 'CLOSED', 'Closed'
        ESCALATED = 'ESCALATED', 'Escalated' 

    class Impact(models.TextChoices):
        INDIVIDUAL = 'INDIVIDUAL', 'Individual'
        DEPARTMENT = 'DEPARTMENT', 'Department'
        SITE = 'SITE', 'Site'
        ORGANIZATION = 'ORGANIZATION', 'Organization'

    class Urgency(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        CRITICAL = 'CRITICAL', 'Critical'

    class Priority(models.TextChoices):
        P1 = 'P1', 'P1 - Critical'
        P2 = 'P2', 'P2 - High'
        P3 = 'P3', 'P3 - Medium'
        P4 = 'P4', 'P4 - Low'

    # Core identification
    number = models.CharField(max_length=50, unique=True, editable=False)  # e.g., TCK-2243
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.INCIDENT)
    title = models.CharField(max_length=255)
    description = models.TextField()

    # Categorization
    category = models.ForeignKey('common.Category', on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='tickets')
    impact = models.CharField(max_length=20, choices=Impact.choices, default=Impact.INDIVIDUAL)
    urgency = models.CharField(max_length=20, choices=Urgency.choices, default=Urgency.MEDIUM)
    priority = models.CharField(max_length=2, choices=Priority.choices, editable=False)  # computed from impact+urgency

    # Status & assignment
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.NEW)
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                  related_name='requested_tickets')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='assigned_tickets')
    queue = models.CharField(max_length=100, blank=True)  # e.g., "Network Team", "Application Support"

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    # SLA targets (placeholders – will be managed by the SLA scheduler)
    response_due_at = models.DateTimeField(null=True, blank=True)
    resolution_due_at = models.DateTimeField(null=True, blank=True)

    # Related asset (CMDB-lite, optional)
    asset_id = models.CharField(max_length=100, blank=True)  # link to an asset record later
    
    # ========== NEW FIELDS FOR ASSET FULFILLMENT ==========
    
    # Track if this is an asset request (set during creation)
    is_asset_request = models.BooleanField(default=False)
    
    # Link to the assigned asset (set during fulfillment)
    assigned_asset = models.ForeignKey(
        'Asset',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets'
    )
    
    # Fulfillment tracking (set during fulfillment)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    fulfilled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fulfilled_tickets'
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'queue']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['requester', 'created_at']),
            models.Index(fields=['number']),
            # NEW: Index for asset fulfillment queries
            models.Index(fields=['status', 'is_asset_request']),
        ]

    def __str__(self):
        return f"{self.number} - {self.title}"

    def save(self, *args, **kwargs):
        # Compute priority based on impact x urgency (standard ITIL matrix)
        if not self.priority:
            impact_score = {
                self.Impact.INDIVIDUAL: 1,
                self.Impact.DEPARTMENT: 2,
                self.Impact.SITE: 3,
                self.Impact.ORGANIZATION: 4
            }.get(self.impact, 1)

            urgency_score = {
                self.Urgency.LOW: 1,
                self.Urgency.MEDIUM: 2,
                self.Urgency.HIGH: 3,
                self.Urgency.CRITICAL: 4
            }.get(self.urgency, 1)

            # Standard 4x4 matrix
            if impact_score == 1:
                if urgency_score <= 3:
                    self.priority = self.Priority.P4
                else:
                    self.priority = self.Priority.P3
            elif impact_score == 2:
                if urgency_score <= 2:
                    self.priority = self.Priority.P4
                elif urgency_score == 3:
                    self.priority = self.Priority.P3
                else:
                    self.priority = self.Priority.P2
            elif impact_score == 3:
                if urgency_score == 1:
                    self.priority = self.Priority.P4
                elif urgency_score == 2:
                    self.priority = self.Priority.P3
                elif urgency_score == 3:
                    self.priority = self.Priority.P2
                else:
                    self.priority = self.Priority.P1
            else:  # impact = Organization
                if urgency_score == 1:
                    self.priority = self.Priority.P3
                elif urgency_score == 2:
                    self.priority = self.Priority.P2
                else:
                    self.priority = self.Priority.P1
        super().save(*args, **kwargs)


class TicketComment(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = 'PUBLIC', 'Public'
        INTERNAL = 'INTERNAL', 'Internal'

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField()
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author} on {self.ticket}"


class Attachment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments')
    comment = models.ForeignKey(TicketComment, on_delete=models.SET_NULL, null=True, blank=True)
    file = models.FileField(upload_to='attachments/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    content_type = models.CharField(max_length=100, blank=True)  # MIME type
    size = models.PositiveIntegerField(default=0)
    hash = models.CharField(max_length=64, blank=True)  # SHA-256 for integrity

    def __str__(self):
        return self.filename


class TicketActivityLog(models.Model):
    """Immutable audit trail for ticket changes (append-only)."""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=50)  # e.g., 'status_changed', 'assigned', 'commented'
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    details = models.JSONField(default=dict, blank=True)  # before/after values
    correlation_id = models.CharField(max_length=100, blank=True)  # for grouping events
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        # Enforce append-only: no updates/deletes allowed at application level
        # We'll use database permissions or model methods to prevent modifications

    def __str__(self):
        return f"{self.action} on {self.ticket} by {self.actor}"
    
class BusinessCalendar(models.Model):
    name = models.CharField(max_length=100)
    workdays = models.JSONField(default=list)   # [0,1,2,3,4] = Mon-Fri
    work_start = models.TimeField(default=datetime.time(8, 0))
    work_end = models.TimeField(default=datetime.time(18, 0))
    holidays = models.JSONField(default=list)   # ["2026-01-01", ...]

    @property
    def workday_names(self):
        mapping = {
            0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun'
        }
        return [mapping.get(int(d), str(d)) for d in self.workdays]

    def __str__(self):
        return self.name


class SLA(models.Model):
    priority = models.CharField(max_length=2, choices=Ticket.Priority.choices, unique=True)
    response_minutes = models.PositiveIntegerField()
    resolution_minutes = models.PositiveIntegerField()
    calendar = models.ForeignKey(BusinessCalendar, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"SLA for {self.get_priority_display()}"


class EscalationRule(models.Model):
    TIMER_CHOICES = [('response', 'Response'), ('resolution', 'Resolution')]
    ACTION_CHOICES = [
        ('notify', 'Notify'),
        ('reassign', 'Reassign'),
        ('add_watcher', 'Add Watcher'),
    ]

    priority = models.CharField(max_length=2, choices=Ticket.Priority.choices)
    timer_type = models.CharField(max_length=20, choices=TIMER_CHOICES)
    threshold_percent = models.PositiveIntegerField()  # e.g., 75 means at 75% of SLA
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    notify_role = models.CharField(max_length=20, choices=User.Role.choices, null=True, blank=True)
    reassign_to_role = models.CharField(max_length=20, choices=User.Role.choices, null=True, blank=True)

    def __str__(self):
        return f"Escalation {self.get_action_type_display()} at {self.threshold_percent}% of {self.get_timer_type_display()} for {self.get_priority_display()}"
    
class Macro(models.Model):
    class Type(models.TextChoices):
        COMMENT = 'COMMENT', 'Comment'
        REASSIGN_REASON = 'REASSIGN_REASON', 'Reassign Reason'
        RETURN_REASON = 'RETURN_REASON', 'Return Reason'
    class Visibility(models.TextChoices):
        PUBLIC = 'PUBLIC', 'Public'
        INTERNAL = 'INTERNAL', 'Internal'

    title = models.CharField(max_length=100)
    body = models.TextField()
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.COMMENT)
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

# apps/tickets/models.py

class Asset(models.Model):
    class AssetType(models.TextChoices):
        COMPUTER = 'COMPUTER', 'Computer'
        LAPTOP = 'LAPTOP', 'Laptop'
        SERVER = 'SERVER', 'Server'
        NETWORK = 'NETWORK', 'Network Device'
        PRINTER = 'PRINTER', 'Printer'
        SOFTWARE = 'SOFTWARE', 'Software License'
        OTHER = 'OTHER', 'Other'

     # Add location choices
    class Location(models.TextChoices):
        HQ = 'HQ', 'Headquarters'
        BRANCH_A = 'BRANCH_A', 'Branch A - Lagos'
        BRANCH_B = 'BRANCH_B', 'Branch B - Abuja'
        BRANCH_C = 'BRANCH_C', 'Branch C - Port Harcourt'
        WAREHOUSE = 'WAREHOUSE', 'Warehouse'
        DATA_CENTER = 'DATA_CENTER', 'Data Center'
        OTHER = 'OTHER', 'Other'  # <-- This triggers custom input

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        IN_STORE = 'IN_STORE', 'In Store'          # unassigned, available
        MAINTENANCE = 'MAINTENANCE', 'Maintenance'
        DAMAGED = 'DAMAGED', 'Damaged'              # pending scrap approval
        SCRAPPED = 'SCRAPPED', 'Scrapped'           # removed from inventory
        RETIRED = 'RETIRED', 'Retired'              # legacy, can be merged with SCRAPPED
        OTHER = 'OTHER', 'Other'  # <-- This triggers custom input


    # Basic info
    name = models.CharField(max_length=200)
    asset_type = models.CharField(max_length=20, default=AssetType.COMPUTER)
    serial_number = models.CharField(max_length=100, blank=True)

    # NEW FIELDS
    tracking_id = models.CharField(max_length=50, unique=True, editable=False)  # auto-generated
    model = models.CharField(max_length=100, blank=True)
    manufacturer = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=200, blank=True, default=Location.HQ)
    warranty_expiry = models.DateField(null=True, blank=True)
    warranty_duration_years = models.PositiveSmallIntegerField(default=0, help_text="Warranty duration in years")
    assigned_to_department = models.CharField(max_length=50, blank=True)

    # Assignment & status
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_assets')
    status = models.CharField(max_length=20, default=Status.ACTIVE)

    # Scrap approval workflow
    scrap_approved = models.BooleanField(default=False)
    scrap_approved_at = models.DateTimeField(null=True, blank=True)
    scrap_approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_scraps')

    # Timestamps
    purchase_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def get_reassignment_count(self):
        """Returns the number of times this asset has been reassigned (excluding initial assignment)."""
        # If we have a cached value, use it
        if hasattr(self, '_reassignment_count'):
            return self._reassignment_count
        
        # Get all ASSIGNED logs in order
        assigned_logs = self.logs.filter(
            action=AssetLog.Action.ASSIGNED
        ).order_by('created_at')
        
        # Count all assignments after the first one (these are reassignments)
        count = max(0, assigned_logs.count() - 1)
        self._reassignment_count = count
        return count

    def has_been_reassigned(self):
        """Returns True if this asset has been reassigned at least once."""
        return self.get_reassignment_count() > 0

    def get_first_assignment(self):
        """Returns the first person this asset was assigned to."""
        first_log = self.logs.filter(
            action=AssetLog.Action.ASSIGNED
        ).order_by('created_at').first()
        
        if first_log and first_log.details:
            return first_log.details.get('to')
        return None

    def get_assignment_history(self):
        """
        Returns a list of assignment history entries including the initial assignment.
        Each entry contains: {'from': user or None, 'to': user or None, 'timestamp': datetime, 'actor': user}
        """
        history = []
        
        # Get all ASSIGNED and UNASSIGNED logs for this asset
        logs = self.logs.filter(
            action__in=[AssetLog.Action.ASSIGNED, AssetLog.Action.UNASSIGNED]
        ).order_by('created_at')
        
        for log in logs:
            details = log.details or {}
            history.append({
                'from_user': details.get('from'),
                'to_user': details.get('to'),
                'timestamp': log.created_at,
                'actor': log.actor.get_full_name() if log.actor else 'System',
                'action': log.action
            })
        
        return history


    def save(self, *args, **kwargs):
        if not self.tracking_id:
            # Generate tracking ID: AST-YYYY-XXXX (e.g., AST-2025-0042)
            year = timezone.now().year
            last_asset = Asset.objects.filter(tracking_id__startswith=f'AST-{year}').order_by('tracking_id').last()
            if last_asset:
                # Extract numeric part after last dash
                parts = last_asset.tracking_id.split('-')
                if len(parts) == 3:
                    try:
                        num = int(parts[2]) + 1
                    except ValueError:
                        num = 1
                else:
                    num = 1
            else:
                num = 1
            self.tracking_id = f'AST-{year}-{num:04d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tracking_id} - {self.name}"


class AssetLog(models.Model):
    """Audit trail for asset changes"""
    class Action(models.TextChoices):
        CREATED = 'CREATED', 'Created'
        UPDATED = 'UPDATED', 'Updated'
        ASSIGNED = 'ASSIGNED', 'Assigned'
        UNASSIGNED = 'UNASSIGNED', 'Unassigned'
        STATUS_CHANGED = 'STATUS_CHANGED', 'Status Changed'
        SCRAP_REQUESTED = 'SCRAP_REQUESTED', 'Scrap Requested'
        SCRAP_APPROVED = 'SCRAP_APPROVED', 'Scrap Approved'
        SCRAP_REJECTED = 'SCRAP_REJECTED', 'Scrap Rejected'

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=20, choices=Action.choices)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} on {self.asset.tracking_id} by {self.actor}"

class RemoteConnector(models.Model):
    name = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=False)
    instructions_for_requester = models.TextField(
        default="1. Open Quick Assist (search in Windows start menu).\n2. Click 'Get assistance'.\n3. Wait for the agent to provide a 6-digit code.\n4. Enter the code and allow screen sharing.\n5. The session will begin."
    )
    instructions_for_agent = models.TextField(
        default="1. Open Quick Assist.\n2. Click 'Help someone'.\n3. A 6-digit code appears – share it with the user.\n4. The code expires in about 10 minutes.\n5. Once the user enters the code, you will have control."
    )
    # Future fields for API connectors (not used now)
    api_endpoint = models.CharField(max_length=200, blank=True)
    api_key = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class RemoteSession(models.Model):
    STATUS_CHOICES = [
        ('REQUESTED', 'Requested'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('STARTED', 'Started'),
        ('ENDED', 'Ended'),
        ('EXPIRED', 'Expired'),   # optional, if code expires
    ]
    ticket = models.ForeignKey('Ticket', on_delete=models.CASCADE, related_name='remote_sessions')
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='requested_remote_sessions')
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='agent_remote_sessions')
    connector = models.ForeignKey(RemoteConnector, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='REQUESTED')
    session_code = models.CharField(max_length=20, blank=True)   # agent can store the code (optional)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Remote session for ticket {self.ticket.number} ({self.status})"

