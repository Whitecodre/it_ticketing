from django.shortcuts import render
from django.http import HttpResponse,JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.middleware.csrf import get_token
from .models import Notification

@login_required
def unread_count(request):
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return render(request, 'partials/notification_badge.html', {'count': count})

@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    # After marking all as read, count is always 0 → badge will be hidden
    return render(request, 'partials/notification_badge.html', {'count': 0})

@login_required
@require_POST
def mark_read(request, pk):
    try:
        notification = Notification.objects.get(pk=pk, recipient=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'status': 'ok'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error'}, status=404)
    
@login_required
def list_notifications(request):
    # Get all notifications for the user, newest first
    all_notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    unread = all_notifications.filter(is_read=False).count()
    notifications = all_notifications[:10]   # slice after counting
    return render(request, 'partials/notification_dropdown.html', {
        'notifications': notifications,
        'unread': unread,
        'csrf_token': get_token(request),
    })

