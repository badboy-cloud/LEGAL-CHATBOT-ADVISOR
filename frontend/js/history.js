// history.js - Renders system audit logs and upload history in tables

document.addEventListener('DOMContentLoaded', () => {
    if (!window.location.pathname.includes('history.html')) return;
    loadHistoryTables();
    
    // Wire up filter controls
    const searchInput = document.getElementById('history-search');
    if (searchInput) {
        searchInput.addEventListener('input', filterHistoryTables);
    }
    const typeSelect = document.getElementById('history-type-filter');
    if (typeSelect) {
        typeSelect.addEventListener('change', filterHistoryTables);
    }
});

async function loadHistoryTables() {
    try {
        const role = localStorage.getItem('role') || 'User';
        let docs = [];
        let logs = [];
        
        // Try fetching admin logs if Admin role; otherwise catch 403 gracefully
        try {
            if (role === 'Admin') {
                docs = await fetchWithAuth('/api/admin/documents');
                logs = await fetchWithAuth('/api/admin/logs');
            } else {
                // Fallback / mock histories for standard user
                docs = [];
                logs = [];
            }
        } catch (fetchErr) {
            console.warn('History fetch blocked (insufficient permissions):', fetchErr);
        }

        // Render Uploaded Documents Table
        const docsBody = document.getElementById('docs-history-table-body');
        if (docsBody) {
            docsBody.innerHTML = '';
            if (docs.length === 0) {
                docsBody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No uploaded documents found. (Admin privilege required)</td></tr>';
            } else {
                docs.forEach(doc => {
                    const tr = document.createElement('tr');
                    tr.className = 'history-row-item';
                    tr.dataset.type = doc.document_type;
                    tr.dataset.name = doc.filename.toLowerCase();
                    tr.innerHTML = `
                        <td><strong>${doc.id}</strong></td>
                        <td>${doc.filename}</td>
                        <td><span class="badge bg-dark border border-secondary text-warning">${doc.document_type.toUpperCase()}</span></td>
                        <td>${formatTimestamp(doc.upload_timestamp)}</td>
                        <td class="text-muted"><small>${doc.file_path}</small></td>
                    `;
                    docsBody.appendChild(tr);
                });
            }
        }

        // Render Audit Logs Table
        const logsBody = document.getElementById('logs-history-table-body');
        if (logsBody) {
            logsBody.innerHTML = '';
            if (logs.length === 0) {
                logsBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No security audit logs found. (Admin privilege required)</td></tr>';
            } else {
                logs.forEach(log => {
                    const tr = document.createElement('tr');
                    tr.className = 'history-row-item';
                    tr.dataset.type = 'audit';
                    tr.dataset.name = log.action.toLowerCase() + ' ' + log.username.toLowerCase();
                    tr.innerHTML = `
                        <td><small class="text-muted">${formatTimestamp(log.timestamp)}</small></td>
                        <td><strong>${log.username}</strong></td>
                        <td><span class="badge bg-secondary">${log.user_role}</span></td>
                        <td>${log.action}</td>
                        <td><span class="badge bg-${log.status === 'success' ? 'success' : 'danger'}">${log.status.toUpperCase()}</span></td>
                        <td>${log.processing_time.toFixed(3)}s</td>
                    `;
                    logsBody.appendChild(tr);
                });
            }
        }

    } catch (err) {
        console.error('Failed to load history data:', err);
    }
}

function filterHistoryTables() {
    const searchVal = (document.getElementById('history-search').value || '').toLowerCase().trim();
    const typeVal = document.getElementById('history-type-filter').value || 'all';

    const rows = document.querySelectorAll('.history-row-item');
    rows.forEach(row => {
        const rowType = row.dataset.type;
        const rowName = row.dataset.name;
        
        let typeMatch = (typeVal === 'all') || (rowType === typeVal);
        let searchMatch = !searchVal || rowName.includes(searchVal);
        
        if (typeMatch && searchMatch) {
            row.classList.remove('d-none');
        } else {
            row.classList.add('d-none');
        }
    });
}
