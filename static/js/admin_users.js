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