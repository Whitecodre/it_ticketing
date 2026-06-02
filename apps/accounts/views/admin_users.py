from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

def is_admin(user):
    return user.role in ['ADMIN', 'SUPERADMIN']

@login_required
@user_passes_test(is_admin)
def admin_user_list(request):
    query = request.GET.get('q', '')
    role_filter = request.GET.get('role', '')
    department_filter = request.GET.get('department', '')
    page = request.GET.get('page', 1)

    users = User.objects.all()
    if query:
        users = users.filter(
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )
    if role_filter:
        users = users.filter(role=role_filter)
    if department_filter:
        users = users.filter(department=department_filter)

    paginator = Paginator(users, 15)
    page_obj = paginator.get_page(page)

    context = {
        'users': page_obj,
        'query': query,
        'role_filter': role_filter,
        'department_filter': department_filter,
        'role_choices': User.Role.choices,
        'department_choices': User.DEPARTMENT_CHOICES,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'partials/user_table.html', context)
    return render(request, 'admin/user_management.html', context)


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_user_create(request):
    email = request.POST.get('email')
    first_name = request.POST.get('first_name')
    last_name = request.POST.get('last_name')
    role = request.POST.get('role', 'END_USER')
    if role == 'SUPERADMIN' and request.user.role != 'SUPERADMIN':
        return JsonResponse({'error': 'Only a Superadmin can create another Superadmin.'}, status=403)
    department = request.POST.get('department', '')
    password = request.POST.get('password')

    if not email or not password:
        return JsonResponse({'error': 'Email and password are required.'}, status=400)

    if User.objects.filter(email=email).exists():
        return JsonResponse({'error': 'User with this email already exists.'}, status=400)

    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        role=role,
        department=department,
        is_active=True
    )
    return JsonResponse({'status': 'ok', 'user_id': user.pk})


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user.role == 'SUPERADMIN' and request.user.role != 'SUPERADMIN':
        return JsonResponse({'error': 'You cannot edit a Superadmin.'}, status=403)

    new_role = request.POST.get('role', user.role)
    if new_role == 'SUPERADMIN' and request.user.role != 'SUPERADMIN':
        return JsonResponse({'error': 'Only a Superadmin can assign the Superadmin role.'}, status=403)

    new_is_active = request.POST.get('is_active', 'true') == 'true'
    if not new_is_active and user == request.user:
        return JsonResponse({'error': 'You cannot deactivate your own account.'}, status=400)
    if not new_is_active and user.role in ['ADMIN', 'SUPERADMIN']:
        active_admins = User.objects.filter(role__in=['ADMIN', 'SUPERADMIN'], is_active=True).count()
        if active_admins <= 1:
            return JsonResponse({'error': 'Cannot deactivate the last admin/superadmin.'}, status=400)

    user.first_name = request.POST.get('first_name', user.first_name)
    user.last_name = request.POST.get('last_name', user.last_name)
    user.role = new_role
    user.department = request.POST.get('department', user.department)
    user.is_active = new_is_active
    user.save()
    return JsonResponse({'status': 'ok'})


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_user_toggle_active(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user.role == 'SUPERADMIN' and request.user.role != 'SUPERADMIN':
        return JsonResponse({'error': 'Only a Superadmin can modify another Superadmin.'}, status=403)
    if user == request.user:
        return JsonResponse({'error': 'You cannot deactivate your own account.'}, status=400)
    if not user.is_active:
        # reactivating is always allowed
        pass
    else:
        # deactivating: check if this is the last active admin/superadmin
        if user.role in ['ADMIN', 'SUPERADMIN']:
            active_admins = User.objects.filter(role__in=['ADMIN', 'SUPERADMIN'], is_active=True).count()
            if active_admins <= 1:
                return JsonResponse({'error': 'Cannot deactivate the last admin/superadmin.'}, status=400)
    user.is_active = not user.is_active
    user.save()
    return JsonResponse({'status': 'ok', 'is_active': user.is_active})