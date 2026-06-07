// admin_users.js – Admin User Management

// --- Toast system ---
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast-item toast-${type}`;
    toast.innerText = message;
    container.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// --- Refresh table with current filters ---
function refreshTable() {
    const q = document.getElementById('searchInput')?.value || '';
    const role = document.getElementById('roleFilter')?.value || '';
    const dept = document.getElementById('departmentFilter')?.value || '';
    const params = new URLSearchParams({ q, role, department: dept });
    const url = window.adminUsersUrl + '?' + params.toString();
    htmx.ajax('GET', url, { target: '#userTableContainer', swap: 'innerHTML' });
}

// --- Create modal ---
function openCreateModal() { document.getElementById('createUserModal').classList.remove('hidden'); }
function closeCreateModal() { document.getElementById('createUserModal').classList.add('hidden'); }

document.getElementById('createUserForm').addEventListener('submit', function (e) {
    e.preventDefault();
    const form = this;
    fetch(form.action, {
        method: 'POST',
        headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value },
        body: new FormData(form)
    }).then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                closeCreateModal();
                form.reset();
                refreshTable();
                showToast('User created successfully');
            } else {
                showToast(data.error || 'Error creating user', 'error');
            }
        });
});

// --- Edit modal ---
function openEditModal(userId) {
    const row = document.querySelector(`tr[data-user-id="${userId}"]`);
    if (!row) return;
    document.getElementById('editUserId').value = userId;
    document.getElementById('editEmail').value = row.dataset.email;
    document.getElementById('editFirstName').value = row.dataset.firstName;
    document.getElementById('editLastName').value = row.dataset.lastName;
    document.getElementById('editRole').value = row.dataset.role;
    document.getElementById('editDepartment').value = row.dataset.department;
    document.getElementById('editIsActive').checked = row.dataset.isActive === 'true';
    document.getElementById('editUserModal').classList.remove('hidden');
}
function closeEditModal() { document.getElementById('editUserModal').classList.add('hidden'); }

document.getElementById('editUserForm').addEventListener('submit', function (e) {
    e.preventDefault();
    const userId = document.getElementById('editUserId').value;
    const formData = new FormData();
    formData.append('first_name', document.getElementById('editFirstName').value);
    formData.append('last_name', document.getElementById('editLastName').value);
    formData.append('role', document.getElementById('editRole').value);
    formData.append('department', document.getElementById('editDepartment').value);
    formData.append('is_active', document.getElementById('editIsActive').checked);
    fetch(window.adminUserEditUrl.replace('0', userId), {
        method: 'POST',
        headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value },
        body: new URLSearchParams(formData)
    }).then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                closeEditModal();
                refreshTable();
                showToast('User details updated');
            } else {
                showToast(data.error || 'Error updating user', 'error');
            }
        });
});

// --- Toggle active ---
function toggleActive(userId) {
    fetch(window.adminUserToggleUrl.replace('0', userId), {
        method: 'POST',
        headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value }
    }).then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                refreshTable();
                showToast(data.is_active ? 'User activated' : 'User deactivated');
            } else {
                showToast(data.error || 'Error toggling user', 'error');
            }
        });
}

// ===================== PASSWORD MODAL =====================

function openPasswordModal(userId) {
    var row = document.querySelector('tr[data-user-id="' + userId + '"]');
    if (!row) return;

    document.getElementById('passwordUserId').value = userId;

    // Fill user info
    var firstName = row.dataset.firstName || '';
    var lastName = row.dataset.lastName || '';
    var fullName = (firstName + ' ' + lastName).trim() || row.dataset.email || '';
    var role = row.dataset.role || '';
    var department = row.dataset.department || '';

    document.getElementById('passwordUserName').innerText = fullName;
    document.getElementById('passwordUserDetails').innerText =
        'Role: ' + role + ' | Department: ' + (department || 'None');

    document.getElementById('changePasswordModal').classList.remove('hidden');
}

function closePasswordModal() {
    var modal = document.getElementById('changePasswordModal');
    if (!modal) return;
    modal.classList.add('hidden');
    // Clear fields
    document.getElementById('newPassword').value = '';
    document.getElementById('confirmPassword').value = '';
    // Reset visibility to password mode
    var newPwd = document.getElementById('newPassword');
    var confirmPwd = document.getElementById('confirmPassword');
    if (newPwd) newPwd.type = 'password';
    if (confirmPwd) confirmPwd.type = 'password';
    // Reset eye icons
    var newEye = document.getElementById('newEyeIcon');
    var newEyeOff = document.getElementById('newEyeOffIcon');
    var confirmEye = document.getElementById('confirmEyeIcon');
    var confirmEyeOff = document.getElementById('confirmEyeOffIcon');
    if (newEye) newEye.classList.remove('hidden');
    if (newEyeOff) newEyeOff.classList.add('hidden');
    if (confirmEye) confirmEye.classList.remove('hidden');
    if (confirmEyeOff) confirmEyeOff.classList.add('hidden');
}

function togglePasswordVisibility(inputId, eyeId, eyeOffId) {
    var input = document.getElementById(inputId);
    var eye = document.getElementById(eyeId);
    var eyeOff = document.getElementById(eyeOffId);
    if (!input || !eye || !eyeOff) return;
    if (input.type === 'password') {
        input.type = 'text';
        eye.classList.add('hidden');
        eyeOff.classList.remove('hidden');
    } else {
        input.type = 'password';
        eye.classList.remove('hidden');
        eyeOff.classList.add('hidden');
    }
}

// Attach form submit handler after DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    var changePwdForm = document.getElementById('changePasswordForm');
    if (!changePwdForm) return;
    changePwdForm.addEventListener('submit', function(e) {
        e.preventDefault();
        var userId = document.getElementById('passwordUserId').value;
        var password = document.getElementById('newPassword').value;
        var confirm = document.getElementById('confirmPassword').value;

        if (password !== confirm) {
            showToast('Passwords do not match.', 'error');
            return;
        }
        if (password.length < 8) {
            showToast('Password must be at least 8 characters.', 'error');
            return;
        }

        var url = window.adminUserChangePasswordUrl.replace('0', userId);
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: new URLSearchParams({ password: password })
        })
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (data.status === 'ok') {
                closePasswordModal();
                showToast(data.message);
            } else {
                showToast(data.error || 'Error changing password', 'error');
            }
        })
        .catch(function(err) {
            showToast('Network error. Please try again.', 'error');
        });
    });
});