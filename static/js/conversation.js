// conversation.js – loaded only on the agent conversation page

// ----- Details Panel Toggle -----
function toggleDetailsPanel() {
    const panel = document.getElementById('detailsPanel');
    panel.classList.toggle('hidden');
    panel.classList.toggle('md:block');
}

// ----- Status Dropdown -----
function toggleStatusDropdown() {
    const menu = document.getElementById('statusMenu');
    const chevron = document.getElementById('statusChevron');
    menu.classList.toggle('hidden');
    chevron.classList.toggle('rotate-180');
}
document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('statusDropdown');
    const menu = document.getElementById('statusMenu');
    const chevron = document.getElementById('statusChevron');
    if (dropdown && menu && !dropdown.contains(event.target)) {
        menu.classList.add('hidden');
        chevron.classList.remove('rotate-180');
    }
});

// ----- Scroll Timeline to Bottom -----
function scrollTimelineToBottom() {
    const el = document.getElementById('commentTimeline');
    if (el) el.scrollTop = el.scrollHeight;
}
document.addEventListener('DOMContentLoaded', scrollTimelineToBottom);
document.body.addEventListener('htmx:afterSwap', function(evt) {
    if (evt.detail.target.id === 'commentTimeline') {
        scrollTimelineToBottom();
        const newTimeline = document.getElementById('commentTimeline');
        const inner = newTimeline.querySelector('#timelineInner');
        if (inner) {
            const newStatus = inner.getAttribute('data-status');
            if (newStatus) updateStatusChip(newStatus);
        }
    }
});

// Update the header status chip
function updateStatusChip(status) {
    const chipContainer = document.getElementById('ticketStatusChip');
    if (!chipContainer) return;
    const statusMap = {
        'NEW': { cls: 'open', text: 'New' },
        'TRIAGED': { cls: 'open', text: 'Triaged' },
        'ASSIGNED': { cls: 'in-progress', text: 'Assigned' },
        'IN_PROGRESS': { cls: 'in-progress', text: 'In Progress' },
        'PENDING_USER': { cls: 'open', text: 'Pending User' },
        'PENDING_VENDOR': { cls: 'open', text: 'Pending Vendor' },
        'RESOLVED': { cls: 'resolved', text: 'Resolved' },
        'CLOSED': { cls: 'resolved', text: 'Closed' },
    };
    const info = statusMap[status] || { cls: 'open', text: status };
    chipContainer.innerHTML = `<span class="status-chip ${info.cls} text-xs">${info.text}</span>`;
}

// ----- Active Tab for Public/Internal -----
function setActiveTab(mode) {
    const publicSpan = document.getElementById('tabPublic');
    const internalSpan = document.getElementById('tabInternal');
    if (mode === 'public') {
        publicSpan.className = 'px-3 py-1 rounded-full inline-block bg-primary text-white border border-primary';
        internalSpan.className = 'px-3 py-1 rounded-full inline-block bg-background text-text-secondary border border-border';
        document.querySelector('input[value="PUBLIC"]').checked = true;
    } else {
        internalSpan.className = 'px-3 py-1 rounded-full inline-block bg-primary text-white border border-primary';
        publicSpan.className = 'px-3 py-1 rounded-full inline-block bg-background text-text-secondary border border-border';
        document.querySelector('input[value="INTERNAL"]').checked = true;
    }
}

// ----- Macros -----
function insertMacro(body, visibility) {
    const textarea = document.getElementById('commentBody');
    if (textarea) {
        textarea.value = body;
        setActiveTab(visibility.toLowerCase());
        const radios = document.getElementsByName('visibility');
        for (let radio of radios) {
            if (radio.value === visibility) radio.checked = true;
        }
        document.getElementById('macroDropdown').classList.add('hidden');
    }
}

// Close macro dropdown on outside click
document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('macroDropdown');
    const button = document.querySelector('[title="Macros"]');
    if (dropdown && !dropdown.classList.contains('hidden') && !dropdown.contains(event.target) && !button.contains(event.target)) {
        dropdown.classList.add('hidden');
    }
});