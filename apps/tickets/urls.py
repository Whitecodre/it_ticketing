from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    path('new/', views.create_ticket, name='create'),
    path('my/', views.my_ticket_list, name='my_list'),
    path('<int:pk>/', views.ticket_detail, name='detail'),
    path('unassigned/', views.unassigned_queue, name='unassigned'),
    path('assigned/', views.assigned_to_me, name='assigned_to_me'),
    path('claim/<int:pk>/', views.claim_ticket, name='claim_ticket'),
    path('<int:pk>/slideover/', views.agent_ticket_detail, name='slideover'),
    path('<int:pk>/conversation/', views.agent_ticket_conversation, name='conversation'),
    path('<int:pk>/comment-conversation/', views.add_comment_conversation, name='add_comment_conversation'),
    path('<int:pk>/update-status/', views.update_status, name='update_status'),
    path('<int:pk>/details-panel/', views.ticket_details_panel, name='details_panel'),
    path('<int:pk>/edit-subject/', views.edit_subject, name='edit_subject'),
    path('<int:pk>/assign-popover/', views.assign_popover, name='assign_popover'),
    path('<int:pk>/assign-to-me/', views.assign_to_me, name='assign_to_me'),
    path('<int:pk>/assign/<int:user_pk>/', views.assign_specific, name='assign_specific'),
    path('<int:ticket_pk>/followers/remove/<int:user_pk>/', views.remove_follower, name='remove_follower'),
    path('<int:ticket_pk>/followers/add-popover/', views.add_follower_popover, name='add_follower_popover'),
    path('<int:pk>/edit-group-popover/', views.edit_group_popover, name='edit_group_popover'),
    path('<int:pk>/edit-type-popover/', views.edit_type_popover, name='edit_type_popover'),
    path('<int:pk>/edit-priority-popover/', views.edit_priority_popover, name='edit_priority_popover'),
    path('<int:pk>/add-tag-popover/', views.add_tag_popover, name='add_tag_popover'),
    path('<int:pk>/remove-tag/<int:tag_pk>/', views.remove_tag, name='remove_tag'),
    path('macros/', views.macro_list, name='macro_list'),
    path('bulk-action/', views.bulk_action, name='bulk_action'),
    path('team/queue/', views.team_queue, name='team_queue'),
    path('team/reassign/<int:pk>/', views.team_reassign, name='team_reassign'),
    path('audit/', views.audit_log, name='audit_log'),
    path('kb-suggestions/', views.kb_suggestions, name='kb_suggestions'),
    # future: detail, list

    # APPROVER URLS
    path('approver/', views.approver_dashboard, name='approver_dashboard'),
    path('approver/pending/', views.approver_pending, name='approver_pending'),
    path('approver/history/', views.approver_history, name='approver_history'),
    path('approve/<int:pk>/', views.approve_ticket, name='approve_ticket'),
    path('reject/<int:pk>/', views.reject_ticket, name='reject_ticket'),

    # SLA URLS
    path('sla/', views.sla_list, name='sla_management'),
    path('sla/create/', views.sla_create, name='sla_create'),
    path('sla/<int:pk>/delete/', views.sla_delete, name='sla_delete'),
    path('calendar/create/', views.calendar_create, name='calendar_create'),
    path('rule/create/', views.rule_create, name='rule_create'),
    path('rule/<int:pk>/delete/', views.rule_delete, name='rule_delete'),
    ]