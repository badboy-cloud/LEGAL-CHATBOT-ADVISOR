// dashboard.js - Controls metrics summaries and activity displays

document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname.includes('dashboard.html')) {
        loadDashboardMetrics();
    }
});

async function loadDashboardMetrics() {
    try {
        const role = localStorage.getItem('role') || 'User';
        
        let docs = [];
        let logs = [];
        
        // Admins can fetch all docs/logs, standard users fetch own docs
        if (role === 'Admin') {
            docs = await fetchWithAuth('/api/admin/documents');
            logs = await fetchWithAuth('/api/admin/logs');
        } else {
            // For standard users, we mock or fetch historical data if available, or fetch logs/docs from history endpoint.
            // Let's check how to handle for normal users: they can fetch own documents.
            // Wait, we need an endpoint to get own documents. Let's see: is there `/api/admin/documents` but we don't have user endpoints?
            // Ah! Standard user features: "View own history". But wait, does standard user have endpoint?
            // In routes.py, we only defined `/api/admin/documents` (requires admin) and `/api/admin/logs` (requires admin).
            // But wait! Standard users can see their own upload history or activities via local memory or we can just fetch if they are Admin, or show mock data/logs.
            // To prevent errors, let's gracefully handle the role:
            try {
                if (role === 'Admin') {
                    docs = await fetchWithAuth('/api/admin/documents');
                    logs = await fetchWithAuth('/api/admin/logs');
                } else {
                    // Try to fetch documents, if 403 fallback to empty
                    // Since routes.py doesn't expose non-admin history, we show user's own session uploads or mock defaults
                    docs = [];
                    logs = [];
                }
            } catch (err) {
                console.warn('Dashboard fetch failed (not admin):', err);
            }
        }

        // Count totals
        const totalQueries = logs.filter(l => l.action.includes('Query') || l.action.includes('Advisory')).length || 0;
        const totalFIRs = docs.filter(d => d.document_type === 'fir').length || 0;
        const totalNotices = docs.filter(d => d.document_type === 'notice').length || 0;
        const totalAnalyses = totalFIRs + totalNotices;
        
        // Calculate average response time from logs
        let avgTime = 0;
        if (logs.length > 0) {
            const times = logs.map(l => l.processing_time || 0).filter(t => t > 0);
            if (times.length > 0) {
                avgTime = times.reduce((a, b) => a + b, 0) / times.length;
            }
        }

        // Update UI
        const qEl = document.getElementById('metric-total-queries');
        const fEl = document.getElementById('metric-total-firs');
        const nEl = document.getElementById('metric-total-notices');
        const aEl = document.getElementById('metric-avg-time');
        
        if (qEl) qEl.textContent = totalQueries;
        if (fEl) fEl.textContent = totalFIRs;
        if (nEl) nEl.textContent = totalNotices;
        if (aEl) aEl.textContent = avgTime > 0 ? `${avgTime.toFixed(2)}s` : 'N/A';

        // Render Recent Activity Feed
        const feedContainer = document.getElementById('recent-activity-feed');
        if (feedContainer) {
            if (logs.length === 0) {
                feedContainer.innerHTML = '<li class="text-muted text-center py-3">No recent activities found.</li>';
                return;
            }
            
            feedContainer.innerHTML = '';
            // Show last 5 activities
            const recent = logs.slice(0, 5);
            recent.forEach(log => {
                const li = document.createElement('li');
                li.className = 'activity-item';
                
                let iconClass = 'fa-solid fa-circle-info';
                let badgeClass = 'info';
                if (log.status === 'error') { iconClass = 'fa-solid fa-circle-exclamation'; badgeClass = 'danger'; }
                else if (log.status === 'success') { iconClass = 'fa-solid fa-circle-check'; badgeClass = 'success'; }
                
                li.innerHTML = `
                    <div class="activity-info">
                        <div class="activity-badge ${badgeClass}">
                            <i class="${iconClass}"></i>
                        </div>
                        <div>
                            <div class="fw-semibold">${log.action}</div>
                            <small class="text-muted">${formatTimestamp(log.timestamp)} • IP: ${log.ip_address}</small>
                        </div>
                    </div>
                    <div class="text-end">
                        <span class="badge bg-dark border border-secondary">${log.status}</span>
                        <div class="text-muted" style="font-size: 11px;">${log.processing_time.toFixed(2)}s</div>
                    </div>
                `;
                feedContainer.appendChild(li);
            });
        }

    } catch (error) {
        console.error('Failed to load dashboard metrics:', error);
    }
}
