// query.js - Handles Legal Query Analysis submission and tab updates

document.addEventListener('DOMContentLoaded', () => {
    if (!window.location.pathname.includes('query.html')) return;
    
    // Suggest prompt listener
    const chips = document.querySelectorAll('.question-chip');
    const queryInput = document.getElementById('query-input');
    chips.forEach(chip => {
        chip.addEventListener('click', () => {
            if (queryInput) {
                queryInput.value = chip.textContent.trim().replace(/^"|"$/g, '');
                queryInput.focus();
            }
        });
    });

    // Form submit listener
    const form = document.getElementById('query-form');
    if (form) {
        form.addEventListener('submit', handleQuerySubmit);
    }
});

async function handleQuerySubmit(e) {
    e.preventDefault();
    const queryInput = document.getElementById('query-input');
    if (!queryInput || !queryInput.value.trim()) return;

    const query = queryInput.value.trim();
    if (query.length < 10) {
        showAlert('query-alert-container', 'Query must be at least 10 characters long.', 'danger');
        return;
    }

    // Show spinner & reset results UI
    document.getElementById('query-spinner').classList.remove('d-none');
    document.getElementById('query-results-panel').classList.add('d-none');
    document.getElementById('query-alert-container').innerHTML = '';

    try {
        const start = Date.now();
        const data = await fetchWithAuth('/api/analyze', {
            method: 'POST',
            body: JSON.stringify({ query })
        });
        const elapsed = (Date.now() - start) / 1000;

        renderQueryResults(data, elapsed);
    } catch (err) {
        showAlert('query-alert-container', err.message, 'danger');
    } finally {
        document.getElementById('query-spinner').classList.add('d-none');
    }
}

function renderQueryResults(res, elapsed) {
    if (res.status === 'error') {
        showAlert('query-alert-container', `Rejection: ${res.message}`, 'warning');
        return;
    }

    const panel = document.getElementById('query-results-panel');
    panel.classList.remove('d-none');

    // Update Meta Row
    const topic = res.topic || {};
    const topicName = (topic.name || 'N/A').replace(/_/g, ' ').toUpperCase();
    const confidence = ((topic.confidence || 0) * 100).toFixed(1);
    const precedentsCount = (res.precedents || []).length;
    
    document.getElementById('meta-topic-badge').textContent = `Topic: ${topicName} (${confidence}%)`;
    document.getElementById('meta-time-badge').textContent = `Time taken: ${elapsed.toFixed(2)}s`;
    document.getElementById('meta-precedents-badge').textContent = `Cases found: ${precedentsCount}`;

    // Render Advice Tab (Markdown-parsed)
    document.getElementById('advice-content').innerHTML = parseMarkdown(res.legal_advice);

    // Render Statutes Tab
    const statutesContainer = document.getElementById('statutes-content');
    statutesContainer.innerHTML = '';
    const statutes = res.statutes || {};
    if (statutes.details && statutes.details.length > 0) {
        statutes.details.forEach((stat, idx) => {
            const accordionItem = document.createElement('div');
            accordionItem.className = 'accordion-item bg-dark border-secondary mb-2';
            
            const sectionCode = stat.code || stat.section || 'Provision';
            const sectionTitle = stat.title || 'Statute';
            const description = stat.description || stat.text || 'Scope currently unavailable.';
            const penalties = stat.penalties || stat.penalty || 'Enforcement currently unavailable.';
            
            accordionItem.innerHTML = `
                <h2 class="accordion-header" id="heading-stat-${idx}">
                    <button class="accordion-button collapsed bg-dark text-warning border-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-stat-${idx}" aria-expanded="false" aria-controls="collapse-stat-${idx}">
                        <strong>${sectionCode}</strong> - ${sectionTitle}
                    </button>
                </h2>
                <div id="collapse-stat-${idx}" class="accordion-collapse collapse" aria-labelledby="heading-stat-${idx}" data-bs-parent="#statutes-content">
                    <div class="accordion-body text-light">
                        <p class="mb-2"><strong>Provision/Scope:</strong></p>
                        <p class="text-muted">${description}</p>
                        <p class="mb-2"><strong>Enforcement / Penalties:</strong></p>
                        <p class="text-muted">${penalties}</p>
                    </div>
                </div>
            `;
            statutesContainer.appendChild(accordionItem);
        });
    } else {
        statutesContainer.innerHTML = '<div class="alert alert-info bg-dark border-secondary text-info">No specific statutes matched confidently.</div>';
    }

    // Render Precedents Tab
    const precedentsContainer = document.getElementById('precedents-content');
    precedentsContainer.innerHTML = '';
    const precedents = res.precedents || [];
    if (precedents.length > 0) {
        precedents.forEach((caseItem, idx) => {
            const accordionItem = document.createElement('div');
            accordionItem.className = 'accordion-item bg-dark border-secondary mb-2';
            
            const caseName = caseItem.case_name || caseItem.citation || `Case Precedent #${idx + 1}`;
            const caseYear = caseItem.year || 'N/A';
            const court = caseItem.court || 'N/A';
            const facts = caseItem.facts || 'N/A';
            const holding = caseItem.holding || 'N/A';
            const principle = caseItem.principle || 'N/A';
            const similarity = ((caseItem.similarity || caseItem.score || 0) * 100).toFixed(1);
            
            accordionItem.innerHTML = `
                <h2 class="accordion-header" id="heading-prec-${idx}">
                    <button class="accordion-button collapsed bg-dark text-warning border-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-prec-${idx}" aria-expanded="false" aria-controls="collapse-prec-${idx}">
                        <strong>${caseName} (${caseYear})</strong> - [Match: ${similarity}%]
                    </button>
                </h2>
                <div id="collapse-prec-${idx}" class="accordion-collapse collapse" aria-labelledby="heading-prec-${idx}" data-bs-parent="#precedents-content">
                    <div class="accordion-body text-light">
                        <p class="mb-1"><strong>Court:</strong> <span class="text-muted">${court}</span></p>
                        <p class="mb-1"><strong>Key Case Facts:</strong></p>
                        <p class="text-muted">${facts}</p>
                        <p class="mb-1"><strong>Court Decision / Holding:</strong></p>
                        <p class="text-muted">${holding}</p>
                        ${principle && principle !== 'N/A' ? `
                        <p class="mb-1"><strong>Legal Principle Established:</strong></p>
                        <p class="text-muted">${principle}</p>
                        ` : ''}
                    </div>
                </div>
            `;
            precedentsContainer.appendChild(accordionItem);
        });
    } else {
        precedentsContainer.innerHTML = '<div class="alert alert-info bg-dark border-secondary text-info">No highly relevant case precedents found in database.</div>';
    }

    // Populate Raw Response JSON Tab
    document.getElementById('raw-response-json').textContent = JSON.stringify(res, null, 2);
}
