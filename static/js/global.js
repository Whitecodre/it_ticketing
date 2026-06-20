// global.js – loaded on every dashboard page

// Toggling Mobile Search bar
function toggleMobileSearch() {
    const wrapper = document.getElementById('mobileSearchInputWrapper');
    const input = wrapper.querySelector('input');
    const searchIcon = document.getElementById('searchIconSearch');
    const closeIcon = document.getElementById('searchIconClose');
    if (wrapper.classList.contains('w-0')) {
        // Open
        wrapper.classList.remove('w-0', 'ml-0');
        wrapper.classList.add('w-40', 'ml-2');
        setTimeout(() => input.focus(), 100);
        if (searchIcon && closeIcon) {
            searchIcon.classList.add('hidden');
            closeIcon.classList.remove('hidden');
        }
    } else {
        // Close
        wrapper.classList.add('w-0', 'ml-0');
        wrapper.classList.remove('w-40', 'ml-2');
        input.value = '';
        if (searchIcon && closeIcon) {
            searchIcon.classList.remove('hidden');
            closeIcon.classList.add('hidden');
        }
    }
}

// ----- Sidebar Toggle (Mobile) -----
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const backdrop = document.getElementById('sidebarBackdrop');
    sidebar.classList.toggle('-translate-x-full');
    if (window.innerWidth < 768) {
        backdrop.classList.toggle('hidden');
    }
}
function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const backdrop = document.getElementById('sidebarBackdrop');
    sidebar.classList.add('-translate-x-full');
    backdrop.classList.add('hidden');
}

// ----- User Menu Toggle -----
function toggleUserMenu() {
    const dropdown = document.getElementById('userMenuDropdown');
    const chevron = document.getElementById('userMenuChevron');
    if (dropdown.style.display === 'none' || dropdown.style.display === '') {
        dropdown.style.display = 'block';
        chevron.style.transform = 'rotate(180deg)';
    } else {
        dropdown.style.display = 'none';
        chevron.style.transform = 'rotate(0deg)';
    }
}

// Close user menu on outside click
document.addEventListener('click', function(event) {
    const button = document.getElementById('userMenuButton');
    const dropdown = document.getElementById('userMenuDropdown');
    if (button && dropdown && !button.contains(event.target) && !dropdown.contains(event.target)) {
        dropdown.style.display = 'none';
        const chevron = document.getElementById('userMenuChevron');
        if (chevron) chevron.style.transform = 'rotate(0deg)';
    }
});

// ----- DOMContentLoaded: sidebar link close, notifications, touch tooltips -----
document.addEventListener('DOMContentLoaded', function() {
    // Close sidebar on mobile when link clicked
    document.querySelectorAll('#sidebar a').forEach(link => {
        link.addEventListener('click', () => {
            if (window.innerWidth < 768) closeSidebar();
        });
    });

    // Load notifications on bell click
    const bell = document.getElementById('notificationBell');
    if (bell) {
        bell.addEventListener('load-notifications', function() {
            htmx.ajax('GET', window.notificationsUrl || '/notifications/list/', {
                target: '#notificationDropdown',
                swap: 'innerHTML'
            });
        });
    }

    // Touch devices: copy data-tooltip to native title (fallback)
    if ('ontouchstart' in window || navigator.maxTouchPoints > 0) {
        document.querySelectorAll('[data-tooltip]').forEach(el => {
            if (!el.hasAttribute('title')) {
                el.setAttribute('title', el.getAttribute('data-tooltip'));
            }
        });
    }
});

// ----- Notifications Dropdown -----
function toggleNotificationDropdown() {
    const dropdown = document.getElementById('notificationDropdown');
    const bell = document.getElementById('notificationBell');
    if (dropdown.classList.contains('hidden')) {
        htmx.trigger('#notificationBell', 'load-notifications');
    }
    dropdown.classList.toggle('hidden');
}

// Close notification dropdown on outside click
document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('notificationDropdown');
    const bell = document.getElementById('notificationBell');
    if (dropdown && bell && !bell.contains(event.target) && !dropdown.contains(event.target)) {
        dropdown.classList.add('hidden');
    }
});

// ----- Slide‑over -----
function openSlideover() {
    document.getElementById('ticketSlideover').classList.remove('translate-x-full');
    document.getElementById('slideoverBackdrop').classList.remove('hidden');
}
function closeSlideover() {
    document.getElementById('ticketSlideover').classList.add('translate-x-full');
    document.getElementById('slideoverBackdrop').classList.add('hidden');
    setTimeout(() => {
        document.getElementById('slideoverContent').innerHTML = '';
    }, 300);
}

// ----- Floating Tooltips (desktop only) -----
(function() {
    // If touch device, skip floating tooltips
    if ('ontouchstart' in window || navigator.maxTouchPoints > 0) return;

    // Right-aligned tooltip for sidebar
    const tooltip = document.createElement('div');
    tooltip.className = 'floating-tooltip';
    document.body.appendChild(tooltip);
    document.querySelectorAll('.sidebar-link[data-tooltip]').forEach(link => {
        link.addEventListener('mouseenter', function(e) {
            const rect = e.currentTarget.getBoundingClientRect();
            tooltip.textContent = e.currentTarget.getAttribute('data-tooltip');
            tooltip.style.opacity = '1';
            tooltip.style.left = (rect.right + 12) + 'px';
            tooltip.style.top = (rect.top + rect.height / 2) + 'px';
            tooltip.style.transform = 'translateY(-50%)';
        });
        link.addEventListener('mouseleave', function() {
            tooltip.style.opacity = '0';
        });
    });
})();

(function() {
    if ('ontouchstart' in window || navigator.maxTouchPoints > 0) return;

    // Bottom-aligned tooltip for other elements
    const tooltip = document.createElement('div');
    tooltip.className = 'floating-tooltip-extended';
    document.body.appendChild(tooltip);
    document.querySelectorAll('.element-link[data-tooltip]').forEach(el => {
        el.addEventListener('mouseenter', function(e) {
            const rect = e.currentTarget.getBoundingClientRect();
            tooltip.textContent = e.currentTarget.getAttribute('data-tooltip');
            tooltip.style.opacity = '1';
            tooltip.style.left = (rect.left + rect.width / 2) + 'px';
            tooltip.style.top = (rect.bottom + 6) + 'px';
            tooltip.style.transform = 'translateX(-50%)';
        });
        el.addEventListener('mouseleave', function() {
            tooltip.style.opacity = '0';
        });
    });
})();

// ----- CSRF Token for HTMX -----
document.body.addEventListener('htmx:configRequest', function(event) {
    const tokenElem = document.querySelector('[name=csrfmiddlewaretoken]');
    if (tokenElem) {
        event.detail.headers['X-CSRFToken'] = tokenElem.value;
    }
});

// This function must be available globally
function markReadAndGo(url, notificationId) {
    // Mark as read
    fetch('/notifications/mark-read/' + notificationId + '/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    }).then(() => {
        // Update badge count
        htmx.ajax('GET', '/notifications/unread-count/', {target:'#notificationBadge', swap:'innerHTML'});
        // Reload dropdown to reflect read state
        htmx.ajax('GET', '/notifications/list/', {target:'#notificationDropdown', swap:'innerHTML'});
    });
    // Navigate to the ticket URL
    if (url) {
        window.location.href = url;
    }
}
// ========== RICH TEXT EDITOR (contenteditable) ==========
let currentEditableDiv = null;

function initRichTextEditor(divId, hiddenInputId) {
    const editor = document.getElementById(divId);
    const hidden = document.getElementById(hiddenInputId);
    if (!editor || !hidden) return;
    currentEditableDiv = editor;

    // Sync HTML to hidden input before form submit
    const form = editor.closest('form');
    if (form) {
        form.addEventListener('submit', function() {
            hidden.value = editor.innerHTML;
        });
    }

    // Optional: restore draft from localStorage
    const draftKey = editor.getAttribute('data-draft-key');
    if (draftKey) {
        const saved = localStorage.getItem(draftKey);
        if (saved) editor.innerHTML = saved;
        editor.addEventListener('input', function() {
            localStorage.setItem(draftKey, editor.innerHTML);
        });
        // Clear draft after successful submission
        form.addEventListener('htmx:afterRequest', function() {
            localStorage.removeItem(draftKey);
            editor.innerHTML = '';
        });
    }
}

function formatDocument(command, value = null) {
    if (!currentEditableDiv) return;
    currentEditableDiv.focus();
    document.execCommand(command, false, value);
}

// Spinner on form submit
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('form[method="post"]').forEach(function(form) {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="inline-flex items-center"><svg class="animate-spin h-4 w-4 mr-2 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Sending...</span>';
                submitBtn.classList.add('opacity-70');
            }
        });
    });
});