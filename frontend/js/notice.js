// notice.js - Handles Legal Notice Analysis submissions and markdown exports

let activeNoticeReportMarkdown = '';

document.addEventListener('DOMContentLoaded', () => {
    if (!window.location.pathname.includes('notice.html')) return;

    const fileInput = document.getElementById('notice-file-input');
    if (fileInput) {
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                handleNoticeUpload(fileInput.files[0]);
            }
        });
    }

    const downloadBtn = document.getElementById('download-brief-btn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', handleDownloadBrief);
    }
});

async function handleNoticeUpload(file) {
    const check = validateFile(file);
    if (!check.valid) {
        showAlert('notice-alert-container', check.error, 'danger');
        return;
    }

    document.getElementById('notice-upload-progress').classList.remove('d-none');
    document.getElementById('notice-results-panel').classList.add('d-none');
    document.getElementById('notice-alert-container').innerHTML = '';

    const formData = new FormData();
    formData.append('file', file);

    try {
        const start = Date.now();
        const data = await fetchWithAuth('/api/analyze-notice', {
            method: 'POST',
            body: formData
        });
        const elapsed = (Date.now() - start) / 1000;

        document.getElementById('notice-upload-progress').classList.add('d-none');
        renderNoticeResults(data, elapsed);
    } catch (err) {
        document.getElementById('notice-upload-progress').classList.add('d-none');
        showAlert('notice-alert-container', err.message, 'danger');
    }
}

function renderNoticeResults(res, elapsed) {
    const panel = document.getElementById('notice-results-panel');
    panel.classList.remove('d-none');

    // Extract basic meta
    const sender = res.sender || 'Not identified';
    const recipient = res.recipient || 'Not identified';
    const advocate = res.advocate || 'None';
    const noticeDate = res.notice_date || 'Not specified';
    const deadline = res.response_deadline || 'Not specified';

    document.getElementById('notice-meta-sender').textContent = sender;
    document.getElementById('notice-meta-recipient').textContent = recipient;
    document.getElementById('notice-meta-advocate').textContent = advocate;
    document.getElementById('notice-meta-date').textContent = noticeDate;
    document.getElementById('notice-meta-deadline').textContent = deadline;
    document.getElementById('notice-meta-elapsed').textContent = `Processed in ${elapsed.toFixed(2)} seconds`;

    // Overview
    document.getElementById('notice-overview').innerHTML = parseMarkdown(res.ai_explanation || 'No summary available.');

    // Summary Tab
    document.getElementById('tab-notice-summary').innerHTML = parseMarkdown(res.notice_summary || 'No summary available.');
    
    // Key Allegations list
    const allegationsContainer = document.getElementById('notice-allegations');
    allegationsContainer.innerHTML = '';
    const allegations = res.key_allegations || [];
    if (allegations.length > 0) {
        allegations.forEach(item => {
            const li = document.createElement('li');
            li.className = 'text-light mb-2';
            li.innerHTML = `<i class="fa-solid fa-triangle-exclamation text-danger me-2"></i> ${item}`;
            allegationsContainer.appendChild(li);
        });
    } else {
        allegationsContainer.innerHTML = '<li class="text-muted">No explicit allegations identified.</li>';
    }

    // Cited laws tab
    const provisionsContainer = document.getElementById('notice-provisions');
    provisionsContainer.innerHTML = '';
    const provisions = res.legal_provisions || [];
    if (provisions.length > 0) {
        provisions.forEach((prov, idx) => {
            const secName = prov.section || 'Cited Provision';
            const secExp = prov.explanation || 'Explanation not available.';
            
            const div = document.createElement('div');
            div.className = 'accordion-item bg-dark border-secondary mb-2';
            div.innerHTML = `
                <h2 class="accordion-header" id="heading-notice-prov-${idx}">
                    <button class="accordion-button collapsed bg-dark text-warning border-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-notice-prov-${idx}">
                        <strong>${secName}</strong>
                    </button>
                </h2>
                <div id="collapse-notice-prov-${idx}" class="accordion-collapse collapse" data-bs-parent="#notice-provisions">
                    <div class="accordion-body text-light">
                        <p>${secExp}</p>
                    </div>
                </div>
            `;
            provisionsContainer.appendChild(div);
        });
    } else {
        provisionsContainer.innerHTML = '<div class="alert alert-info bg-dark border-secondary text-info">No specific statutory sections cited in the notice.</div>';
    }

    // Demands tab
    const demandsContainer = document.getElementById('notice-demands');
    demandsContainer.innerHTML = '';
    const demands = res.required_actions || [];
    if (demands.length > 0) {
        demands.forEach(act => {
            const li = document.createElement('li');
            li.className = 'text-light mb-2';
            li.innerHTML = `<i class="fa-solid fa-arrow-right-long text-warning me-2"></i> ${act}`;
            demandsContainer.appendChild(li);
        });
    } else {
        demandsContainer.innerHTML = '<li class="text-muted">No specific demanded actions identified.</li>';
    }

    document.getElementById('notice-consequences').textContent = res.possible_consequences || 'Failing to respond may result in legal actions.';

    // Steps tab
    const stepsContainer = document.getElementById('notice-steps');
    stepsContainer.innerHTML = '';
    const recs = res.recommendations || [];
    if (recs.length > 0) {
        recs.forEach(rec => {
            const li = document.createElement('li');
            li.className = 'text-light mb-2';
            li.innerHTML = `<i class="fa-solid fa-circle-check text-success me-2"></i> ${rec}`;
            stepsContainer.appendChild(li);
        });
    } else {
        stepsContainer.innerHTML = `
            <li class="text-light mb-2"><i class="fa-solid fa-circle-check text-success me-2"></i> Read the notice carefully.</li>
            <li class="text-light mb-2"><i class="fa-solid fa-circle-check text-success me-2"></i> Preserve all documents and communications.</li>
            <li class="text-light mb-2"><i class="fa-solid fa-circle-check text-success me-2"></i> Consult a qualified advocate before responding.</li>
        `;
    }

    // Raw text view
    document.getElementById('notice-extracted-text').textContent = res.extracted_text || 'No text extracted.';

    // Compile markdown report brief
    activeNoticeReportMarkdown = `# LEGAL NOTICE ANALYSIS REPORT
Generated on: ${new Date().toISOString().replace('T', ' ').substring(0, 19)}
Powered by Indian Legal Advisor Notice Analyzer

================================================================================
1. NOTICE PROFILE
================================================================================
- Sender: ${sender}
- Recipient: ${recipient}
- Advocate/Law Firm: ${advocate}
- Notice Date: ${noticeDate}
- Response Deadline: ${deadline}

================================================================================
2. SUMMARY & ALLEGATIONS
================================================================================
${res.notice_summary || 'N/A'}

Key Allegations:
${allegations.map(a => `- ${a}`).join('\n')}

================================================================================
3. CITED LAWS & SECTIONS
================================================================================
${provisions.map(p => `- ${p.section}: ${p.explanation}`).join('\n')}

================================================================================
4. AI EXPLANATION & DEMANDS
================================================================================
${res.ai_explanation || 'N/A'}

Demanded Actions:
${demands.map(d => `- ${d}`).join('\n')}

Possible Consequences:
${res.possible_consequences || 'N/A'}

================================================================================
5. RECOMMENDATIONS & NEXT STEPS
================================================================================
${recs.map(r => `- ${r}`).join('\n')}

================================================================================
DISCLAIMER
================================================================================
This analysis is AI-generated for informational purposes only and is not legal advice. Consult a qualified advocate for advice specific to your situation.
`;
}

function handleDownloadBrief() {
    if (!activeNoticeReportMarkdown) return;
    
    const blob = new Blob([activeNoticeReportMarkdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'Legal_Notice_Analysis_Brief.md';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
