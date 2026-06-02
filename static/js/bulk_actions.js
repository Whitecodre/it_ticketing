// bulk_actions.js – loaded on agent queue pages

let bulkSource = window.bulkSource || 'unassigned';

function updateBulkBar() {
    const checked = document.querySelectorAll('.ticket-checkbox:checked');
    const count = checked.length;
    const bar = document.getElementById('bulkActionBar');
    if (bar) {
        if (count === 0) {
            bar.classList.add('hidden');
            bar.classList.remove('flex');
        } else {
            bar.classList.remove('hidden');
            bar.classList.add('flex');
        }
        const selectedCount = document.getElementById('selectedCount');
        if (selectedCount) selectedCount.innerText = count;
        const selectAll = document.getElementById('selectAll');
        if (selectAll) selectAll.checked = (count === document.querySelectorAll('.ticket-checkbox').length && count > 0);
    }
}

function toggleSelectAll(checkbox) {
    const all = document.querySelectorAll('.ticket-checkbox');
    all.forEach(cb => cb.checked = checkbox.checked);
    updateBulkBar();
}

function clearSelection() {
    document.querySelectorAll('.ticket-checkbox').forEach(cb => cb.checked = false);
    const selectAll = document.getElementById('selectAll');
    if (selectAll) selectAll.checked = false;
    updateBulkBar();
}

function submitBulkAction(actionType, value) {
    const selectedIds = [];
    document.querySelectorAll('.ticket-checkbox:checked').forEach(cb => selectedIds.push(cb.value));
    if (selectedIds.length === 0) return;

    fetch(window.bulkActionUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
        },
        body: new URLSearchParams({
            'ticket_ids': selectedIds.join(','),
            'action': actionType,
            'value': value,
            'source': bulkSource,
        })
    }).then(response => response.text())
      .then(html => {
          document.getElementById('ticketTable').innerHTML = html;
      });
}

document.addEventListener('DOMContentLoaded', updateBulkBar);