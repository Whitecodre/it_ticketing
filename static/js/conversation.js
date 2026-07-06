// conversation.js – loaded only on the agent conversation page

// ================================================================
// DETAILS PANEL TOGGLE
// ================================================================
function toggleDetailsPanel() {
    const panel = document.getElementById('detailsPanel');
    if (!panel) return;
    if (window.innerWidth < 640) {
        panel.classList.toggle('w-0');
        panel.classList.toggle('w-full');
    } else {
        panel.classList.toggle('w-0');
        panel.classList.toggle('w-80');
        panel.classList.toggle('w-96');
    }
}

// ================================================================
// STATUS DROPDOWN
// ================================================================
function toggleStatusDropdown() {
    const menu = document.getElementById('statusMenu');
    const chevron = document.getElementById('statusChevron');
    if (!menu || !chevron) return;
    menu.classList.toggle('hidden');
    chevron.classList.toggle('rotate-180');
}

document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('statusDropdown');
    const menu = document.getElementById('statusMenu');
    const chevron = document.getElementById('statusChevron');
    if (dropdown && menu && !dropdown.contains(event.target)) {
        menu.classList.add('hidden');
        if (chevron) chevron.classList.remove('rotate-180');
    }
});

// ================================================================
// SCROLL TIMELINE TO BOTTOM
// ================================================================
function scrollTimelineToBottom() {
    const el = document.getElementById('commentTimeline');
    if (el) el.scrollTop = el.scrollHeight;
}

document.addEventListener('DOMContentLoaded', scrollTimelineToBottom);

document.body.addEventListener('htmx:afterSwap', function(evt) {
    if (evt.detail.target && evt.detail.target.id === 'commentTimeline') {
        scrollTimelineToBottom();
        const newTimeline = document.getElementById('commentTimeline');
        const inner = newTimeline ? newTimeline.querySelector('#timelineInner') : null;
        if (inner) {
            const newStatus = inner.getAttribute('data-status');
            if (newStatus) updateStatusChip(newStatus);
        }
    }
});

// ================================================================
// UPDATE STATUS CHIP
// ================================================================
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
        'PENDING_FULFILLMENT': { cls: 'pending-approval', text: 'Pending Fulfillment' },
        'RESOLVED': { cls: 'resolved', text: 'Resolved' },
        'CLOSED': { cls: 'resolved', text: 'Closed' },
        'APPROVED': { cls: 'approved', text: 'Approved' },
        'ESCALATED': { cls: 'escalated', text: 'Escalated' },
    };
    const info = statusMap[status] || { cls: 'open', text: status };
    chipContainer.innerHTML = `<span class="status-chip ${info.cls} text-xs">${info.text}</span>`;
}

// ================================================================
// ACTIVE TAB FOR PUBLIC/INTERNAL
// ================================================================
function setActiveTab(mode) {
    const publicSpan = document.getElementById('tabPublic');
    const internalSpan = document.getElementById('tabInternal');
    if (!publicSpan || !internalSpan) return;
    
    if (mode === 'public') {
        publicSpan.className = 'px-3 py-1 rounded-full inline-block bg-primary text-white border border-primary';
        internalSpan.className = 'px-3 py-1 rounded-full inline-block bg-background text-text-secondary border border-border';
        const publicRadio = document.querySelector('input[value="PUBLIC"]');
        if (publicRadio) publicRadio.checked = true;
    } else {
        internalSpan.className = 'px-3 py-1 rounded-full inline-block bg-primary text-white border border-primary';
        publicSpan.className = 'px-3 py-1 rounded-full inline-block bg-background text-text-secondary border border-border';
        const internalRadio = document.querySelector('input[value="INTERNAL"]');
        if (internalRadio) internalRadio.checked = true;
    }
}

// ================================================================
// MACROS
// ================================================================
function insertMacro(body, visibility) {
    const editor = document.getElementById('commentEditor');
    if (editor) {
        editor.innerHTML = body;
        setActiveTab(visibility.toLowerCase());
        const radios = document.getElementsByName('visibility');
        for (let radio of radios) {
            if (radio.value === visibility) radio.checked = true;
        }
        const dropdown = document.getElementById('macroDropdown');
        if (dropdown) dropdown.classList.add('hidden');
    }
}

// Close macro dropdown on outside click
document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('macroDropdown');
    const button = document.querySelector('[data-tooltip="Macros"]');
    if (dropdown && !dropdown.classList.contains('hidden') && !dropdown.contains(event.target) && button && !button.contains(event.target)) {
        dropdown.classList.add('hidden');
    }
});

// ================================================================
// FULFILLMENT MODAL
// ================================================================

function openFulfillModal(ticketId) {
    // Remove any existing modal
    const existing = document.getElementById('fulfillModal');
    if (existing) existing.remove();
    
    // Disable body scroll
    document.body.style.overflow = 'hidden';
    
    // Fetch the modal content
    fetch(`/tickets/assets/fulfill-modal/${ticketId}/`)
        .then(response => response.text())
        .then(html => {
            const wrapper = document.createElement('div');
            wrapper.innerHTML = html;
            document.body.appendChild(wrapper.firstElementChild);
            
            // ================================================================
            // KEY: Re-initialize HTMX for dynamically loaded content
            // ================================================================
            const modal = document.getElementById('fulfillModal');
            if (modal && typeof htmx !== 'undefined') {
                htmx.process(modal);
                console.log('✅ HTMX processed for modal');
            }
            
            // Click on backdrop closes modal
            if (modal) {
                modal.addEventListener('click', function(e) {
                    if (e.target === this || e.target.hasAttribute('data-modal-backdrop')) {
                        closeFulfillModal();
                    }
                });
            }
        })
        .catch(error => {
            console.error('Error loading fulfill modal:', error);
            document.body.style.overflow = '';
            if (typeof showToast === 'function') {
                showToast('Error loading fulfillment form.', 'error');
            }
        });
}

function closeFulfillModal() {
    const modal = document.getElementById('fulfillModal');
    if (modal) {
        modal.remove();
    }
    document.body.style.overflow = '';
}

// Close on Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeFulfillModal();
    }
});

// Handle data-close-modal buttons using event delegation
document.addEventListener('click', function(e) {
    const closeBtn = e.target.closest('[data-close-modal]');
    if (closeBtn) {
        e.preventDefault();
        closeFulfillModal();
    }
});