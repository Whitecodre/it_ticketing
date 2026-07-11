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

// ================================================================
// SLIDEOVER FUNCTIONS
// ================================================================

function openSlideover() {
    const panel = document.getElementById('ticketSlideover');
    const backdrop = document.getElementById('slideoverBackdrop');
    if (panel) {
        panel.classList.remove('translate-x-full');
        panel.classList.add('translate-x-0');
        panel.style.transform = 'translateX(0)';
    }
    if (backdrop) {
        backdrop.classList.remove('hidden');
        backdrop.style.display = 'block';
    }
    document.body.style.overflow = 'hidden';
}

function closeSlideover() {
    const panel = document.getElementById('ticketSlideover');
    const backdrop = document.getElementById('slideoverBackdrop');
    if (panel) {
        panel.classList.add('translate-x-full');
        panel.classList.remove('translate-x-0');
        panel.style.transform = 'translateX(100%)';
    }
    if (backdrop) {
        backdrop.classList.add('hidden');
        backdrop.style.display = 'none';
    }
    document.body.style.overflow = '';
    setTimeout(() => {
        const content = document.getElementById('slideoverContent');
        if (content) content.innerHTML = '';
    }, 300);
}

// Make functions globally available
window.openSlideover = openSlideover;
window.closeSlideover = closeSlideover;

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

// ----- Global Confirmation Modal -----
let confirmCallback = null;

function openConfirmationModal(message, title = 'Confirm Action', confirmText = 'Confirm', confirmClass = 'btn-danger', callback) {
    const modal = document.getElementById('confirmationModal');
    const titleEl = document.getElementById('confirmModalTitle');
    const msgEl = document.getElementById('confirmModalMessage');
    const btn = document.getElementById('confirmModalBtn');

    if (titleEl) titleEl.textContent = title;
    if (msgEl) msgEl.textContent = message;
    if (btn) {
        btn.textContent = confirmText;
        btn.className = confirmClass + ' text-sm px-4 py-2 rounded-lg';
        confirmCallback = callback;
        const newBtn = btn.cloneNode(true);
        btn.parentNode.replaceChild(newBtn, btn);
        newBtn.addEventListener('click', function(e) {
            if (typeof confirmCallback === 'function') {
                confirmCallback();
            }
            closeConfirmationModal();
        });
    }

    modal.classList.remove('hidden');
}

function closeConfirmationModal(event) {
    if (event && event.target !== event.currentTarget) return;
    const modal = document.getElementById('confirmationModal');
    modal.classList.add('hidden');
    confirmCallback = null;
}

function closeAttachmentModal() {
    const overlay = document.getElementById('modalOverlay');
    const container = document.getElementById('modalContainer');
    if (overlay) overlay.classList.add('hidden');
    if (container) container.innerHTML = '';
}

// Optional: close on Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeConfirmationModal();
    }
});

// ========== TOAST NOTIFICATIONS ==========

function getIconPath(iconName) {
    const icons = {
        'check-circle': '<circle cx="12" cy="12" r="10"></circle><path d="M9 12l2 2 4-4"></path>',
        'x-circle': '<circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line>',
        'alert-triangle': '<path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line>',
        'info': '<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line>'
    };
    return icons[iconName] || icons.info;
}

function showToast(message, type = 'info') {
    // Ensure container exists
    let container = document.getElementById('toastContainer');
    if (!container) {
        const div = document.createElement('div');
        div.id = 'toastContainer';
        div.className = 'toast-container';
        document.body.appendChild(div);
        container = document.getElementById('toastContainer');
    }
    
    // Map types to config
    const config = {
        'success': { icon: 'check-circle', title: 'Success' },
        'error': { icon: 'x-circle', title: 'Error' },
        'warning': { icon: 'alert-triangle', title: 'Warning' },
        'info': { icon: 'info', title: 'Info' }
    };
    const cfg = config[type] || config.info;
    
    // Create toast
    const toast = document.createElement('div');
    toast.className = `toast-item toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <div class="toast-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    ${getIconPath(cfg.icon)}
                </svg>
            </div>
            <div class="toast-body">
                <div class="toast-title">${cfg.title}</div>
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-dismiss" onclick="this.closest('.toast-item').remove()">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        </div>
        <div class="toast-progress">
            <div class="toast-progress-bar" style="width: 100%;"></div>
        </div>
    `;
    
    container.appendChild(toast);
    
    // Show with animation
    setTimeout(() => toast.classList.add('show'), 10);
    
    // Progress bar animation
    const progressBar = toast.querySelector('.toast-progress-bar');
    const duration = 8000;
    const startTime = Date.now();
    
    function updateProgress() {
        const elapsed = Date.now() - startTime;
        const remaining = Math.max(0, 1 - elapsed / duration);
        if (progressBar) {
            progressBar.style.width = (remaining * 100) + '%';
        }
        if (elapsed < duration) {
            requestAnimationFrame(updateProgress);
        }
    }
    requestAnimationFrame(updateProgress);
    
    // Make toast clickable if URL exists
    if (window.__pendingNotificationUrl) {
        toast.style.cursor = 'pointer';
        toast.addEventListener('click', function() {
            window.location.href = window.__pendingNotificationUrl;
        });
    }
    
    // Auto-dismiss
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, duration);
    
    // Clear pending URL after showing toast
    setTimeout(() => {
        window.__pendingNotificationUrl = null;
    }, 1000);
}

// ========== REASSIGN TRAIL TOOLTIPS (Improved) ==========
(function() {
    // Skip on touch devices - they use click instead
    if ('ontouchstart' in window || navigator.maxTouchPoints > 0) {
        // On touch devices, show on click instead
        document.addEventListener('click', function(e) {
            const indicator = e.target.closest('.reassign-indicator');
            if (indicator) {
                e.preventDefault();
                e.stopPropagation();
                toggleReassignTooltip(indicator);
            }
        });
        return;
    }

    const tooltip = document.createElement('div');
    tooltip.className = 'floating-tooltip-reassign';
    document.body.appendChild(tooltip);

    let currentTarget = null;
    let hideTimeout = null;
    let isHoveringTooltip = false;
    let isHoveringTarget = false;

    // Global function to reinitialize tooltips after HTMX swaps
    window.initReassignTooltips = function() {
        // Remove old tooltip if it exists
        if (tooltip) {
            tooltip.classList.remove('visible');
            tooltip.innerHTML = '';
        }
        currentTarget = null;
        isHoveringTooltip = false;
        isHoveringTarget = false;
        if (hideTimeout) {
            clearTimeout(hideTimeout);
            hideTimeout = null;
        }

        // Reattach event listeners to all indicators
        document.querySelectorAll('.reassign-indicator').forEach(function(el) {
            // Remove old listeners by cloning (clean approach)
            const wrapper = el.closest('.reassign-trigger-wrapper');
            if (wrapper) {
                const newWrapper = wrapper.cloneNode(true);
                wrapper.parentNode.replaceChild(newWrapper, wrapper);
                const newEl = newWrapper.querySelector('.reassign-indicator');
                if (newEl) {
                    attachEvents(newEl);
                }
            }
        });
    };

    function attachEvents(el) {
        el.addEventListener('mouseenter', function(e) {
            isHoveringTarget = true;
            if (hideTimeout) {
                clearTimeout(hideTimeout);
                hideTimeout = null;
            }
            showTooltip(this, e);
        });

        el.addEventListener('mouseleave', function(e) {
            isHoveringTarget = false;
            hideTimeout = setTimeout(function() {
                if (!isHoveringTooltip && !isHoveringTarget) {
                    hideTooltip();
                }
            }, 300);
        });

        // Click also shows tooltip (for accessibility)
        el.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            if (tooltip.classList.contains('visible') && currentTarget === this) {
                hideTooltip();
            } else {
                showTooltip(this, e);
            }
        });
    }

    function showTooltip(target, event) {
        const html = target.getAttribute('data-tooltip-html');
        if (!html) return;

        currentTarget = target;
        tooltip.innerHTML = html;
        tooltip.classList.add('visible');

        // Tooltip hover events
        tooltip.onmouseenter = function() {
            isHoveringTooltip = true;
            if (hideTimeout) {
                clearTimeout(hideTimeout);
                hideTimeout = null;
            }
        };

        tooltip.onmouseleave = function() {
            isHoveringTooltip = false;
            hideTimeout = setTimeout(function() {
                if (!isHoveringTooltip && !isHoveringTarget) {
                    hideTooltip();
                }
            }, 300);
        };

        // Position after content is rendered
        requestAnimationFrame(function() {
            positionTooltip(currentTarget);
        });
    }

    function hideTooltip() {
        tooltip.classList.remove('visible');
        tooltip.innerHTML = '';
        currentTarget = null;
        isHoveringTooltip = false;
        isHoveringTarget = false;
        if (hideTimeout) {
            clearTimeout(hideTimeout);
            hideTimeout = null;
        }
    }

    function positionTooltip(target) {
        const rect = target.getBoundingClientRect();
        const tooltipWidth = Math.min(tooltip.offsetWidth || 320, 400);
        const tooltipHeight = tooltip.offsetHeight || 200;

        // Position centered above or below
        let left = rect.left + rect.width / 2 - tooltipWidth / 2;
        let top = rect.bottom + 8;

        // Keep in viewport horizontally
        if (left < 10) left = 10;
        if (left + tooltipWidth > window.innerWidth - 10) {
            left = window.innerWidth - tooltipWidth - 10;
        }

        // If tooltip goes off bottom, show above
        if (top + tooltipHeight > window.innerHeight - 10) {
            top = rect.top - tooltipHeight - 8;
        }

        tooltip.style.left = left + 'px';
        tooltip.style.top = top + 'px';
        tooltip.style.maxWidth = '400px';
    }

    // Initialize on page load
    document.addEventListener('DOMContentLoaded', function() {
        initReassignTooltips();
    });

    // Reinitialize after HTMX swaps
    document.addEventListener('htmx:afterSwap', function(evt) {
        // If the swap target contains assets table, reinitialize
        if (evt.detail.target && evt.detail.target.id === 'assetTableContainer') {
            setTimeout(function() {
                initReassignTooltips();
            }, 100);
        }
        // Also reinitialize if the target contains .reassign-indicator
        if (evt.detail.target && evt.detail.target.querySelector('.reassign-indicator')) {
            setTimeout(function() {
                initReassignTooltips();
            }, 100);
        }
    });

    // Also listen for htmx:afterSettle
    document.addEventListener('htmx:afterSettle', function(evt) {
        if (evt.detail.target && evt.detail.target.querySelector('.reassign-indicator')) {
            setTimeout(function() {
                initReassignTooltips();
            }, 50);
        }
    });

    // Hide tooltip on scroll or click outside
    window.addEventListener('scroll', function() {
        hideTooltip();
    }, { passive: true });

    document.addEventListener('click', function(e) {
        if (!e.target.closest('.reassign-indicator') && !e.target.closest('.floating-tooltip-reassign')) {
            hideTooltip();
        }
    });

    // Handle escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            hideTooltip();
        }
    });
})();

// ================================================================
// FULFILLMENT MODAL - Global Functions
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
            
            // Re-initialize HTMX for dynamically loaded content
            const modal = document.getElementById('fulfillModal');
            if (modal && typeof htmx !== 'undefined') {
                htmx.process(modal);
                console.log('✅ HTMX processed for modal');
            }
            
            // Click on backdrop closes modal
            if (modal) {
                modal.addEventListener('click', function(e) {
                    if (e.target === this) {
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