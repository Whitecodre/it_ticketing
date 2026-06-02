document.addEventListener('keydown', function(e) {
    const target = e.target;

    // ---------- Enter in comment textarea → submit form ----------
    if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
        const textarea = document.getElementById('commentBody');
        if (textarea && target === textarea) {
            e.preventDefault();
            const form = document.getElementById('commentForm');
            if (form) {
                form.dispatchEvent(new Event('submit', {cancelable: true, bubbles: true}));
                return;
            }
        }
    }

    // ---------- Don't interfere with other inputs ----------
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return;
    }

    // ---------- Esc: close slideover, details panel, status dropdown ----------
    if (e.key === 'Escape') {
        if (typeof closeSlideover === 'function') closeSlideover();
        closeDetailsPanelIfOpen();
        closeStatusMenuIfOpen();
    }

    // ---------- J/K: navigate ticket rows (queue pages) ----------
    if (document.querySelector('.ticket-checkbox') && (e.key === 'j' || e.key === 'k')) {
        e.preventDefault();
        const rows = Array.from(document.querySelectorAll('tr.group'));
        if (rows.length === 0) return;
        let currentIdx = rows.findIndex(r => r.classList.contains('highlighted-row'));
        if (currentIdx === -1) currentIdx = 0;
        rows.forEach(r => r.classList.remove('highlighted-row'));
        if (e.key === 'j') currentIdx = (currentIdx + 1) % rows.length;
        else currentIdx = (currentIdx - 1 + rows.length) % rows.length;
        rows[currentIdx].classList.add('highlighted-row');
        rows[currentIdx].scrollIntoView({block: 'nearest', behavior: 'smooth'});
    }

    // ---------- Enter: open highlighted ticket (queue pages) ----------
    if (e.key === 'Enter' && document.querySelector('.ticket-checkbox')) {
        const highlighted = document.querySelector('.highlighted-row');
        if (highlighted) {
            e.preventDefault();
            const viewLink = highlighted.querySelector('a[href*="conversation"], a[href*="slideover"]');
            if (viewLink) {
                if (viewLink.getAttribute('hx-get')) viewLink.click();
                else window.location.href = viewLink.href;
            }
        }
    }
});

function closeDetailsPanelIfOpen() {
    const panel = document.getElementById('detailsPanel');
    if (panel && typeof toggleDetailsPanel === 'function') {
        if (!panel.classList.contains('hidden') && !panel.classList.contains('w-0')) {
            toggleDetailsPanel();
        }
    }
}

function closeStatusMenuIfOpen() {
    const menu = document.getElementById('statusMenu');
    const chevron = document.getElementById('statusChevron');
    if (menu && !menu.classList.contains('hidden')) {
        menu.classList.add('hidden');
        if (chevron) chevron.classList.remove('rotate-180');
    }
}