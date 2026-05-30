// global.js – loaded on every dashboard page

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

// Close sidebar on mobile when link clicked
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('#sidebar a').forEach(link => {
        link.addEventListener('click', () => {
            if (window.innerWidth < 768) closeSidebar();
        });
    });
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

// Load notifications on bell click (set up once)
document.addEventListener('DOMContentLoaded', function() {
    const bell = document.getElementById('notificationBell');
    if (bell) {
        bell.addEventListener('load-notifications', function() {
            htmx.ajax('GET', window.notificationsUrl || '/notifications/list/', {
                target: '#notificationDropdown',
                swap: 'innerHTML'
            });
        });
    }
});

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

// ----- Floating Tooltips (sidebar + extended) -----
(function() {
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
    fetch('{% url "notifications:mark_read" 999 %}'.replace('999', notificationId), {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    }).then(() => {
        // Update badge count
        htmx.ajax('GET', '{% url "notifications:unread_count" %}', {target:'#notificationBadge', swap:'innerHTML'});
        // Reload dropdown to reflect read state
        htmx.ajax('GET', '{% url "notifications:list" %}', {target:'#notificationDropdown', swap:'innerHTML'});
    });
    // Navigate to the ticket URL
    if (url) {
        window.location.href = url;
    }
}