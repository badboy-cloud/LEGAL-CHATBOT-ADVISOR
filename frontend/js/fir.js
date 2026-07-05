// fir.js - Handles drag-and-drop uploads, FIR OCR processing, and contextual chat

let activeFIRText = ''; // Stores text content of processed FIR for chat context
let firChatHistory = [];

document.addEventListener('DOMContentLoaded', () => {
    if (!window.location.pathname.includes('fir.html')) return;

    const dragArea = document.getElementById('drag-drop-area');
    const fileInput = document.getElementById('fir-file-input');

    if (dragArea && fileInput) {
        // Drag events
        dragArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            dragArea.classList.add('border-warning');
        });
        
        dragArea.addEventListener('dragleave', () => {
            dragArea.classList.remove('border-warning');
        });
        
        dragArea.addEventListener('drop', (e) => {
            e.preventDefault();
            dragArea.classList.remove('border-warning');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                handleFIRUpload(files[0]);
            }
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                handleFIRUpload(fileInput.files[0]);
            }
        });
    }

    // Contextual Chat submit listener
    const chatForm = document.getElementById('fir-ctx-chat-form');
    if (chatForm) {
        chatForm.addEventListener('submit', handleFIRContextualChat);
    }
});

async function handleFIRUpload(file) {
    // Validate File
    const check = validateFile(file);
    if (!check.valid) {
        showAlert('fir-alert-container', check.error, 'danger');
        return;
    }

    // Reset UIs
    document.getElementById('fir-upload-progress').classList.remove('d-none');
    document.getElementById('fir-results-panel').classList.add('d-none');
    document.getElementById('fir-alert-container').innerHTML = '';
    
    // Simulate upload/OCR progress steps
    const progressBar = document.getElementById('fir-progress-bar');
    progressBar.style.width = '20%';
    progressBar.textContent = 'Uploading...';

    const formData = new FormData();
    formData.append('file', file);

    try {
        progressBar.style.width = '50%';
        progressBar.textContent = 'Extracting Text (OCR)...';

        const start = Date.now();
        const data = await fetchWithAuth('/api/analyze-fir', {
            method: 'POST',
            body: formData
        });
        const elapsed = (Date.now() - start) / 1000;

        progressBar.style.width = '100%';
        progressBar.textContent = 'Analysis Completed!';
        
        setTimeout(() => {
            document.getElementById('fir-upload-progress').classList.add('d-none');
            renderFIRResults(data, elapsed);
        }, 800);

    } catch (err) {
        document.getElementById('fir-upload-progress').classList.add('d-none');
        showAlert('fir-alert-container', err.message, 'danger');
    }
}

function renderFIRResults(res, elapsed) {
    const panel = document.getElementById('fir-results-panel');
    panel.classList.remove('d-none');

    // Save context for chat
    activeFIRText = res.extracted_text || '';
    firChatHistory = [];
    
    // Reset Chat panel display
    const chatMessages = document.getElementById('fir-ctx-chat-messages');
    if (chatMessages) {
        chatMessages.innerHTML = '<div class="message-bubble assistant">FIR loaded! Ask me any specific questions about this incident or its legal consequences below.</div>';
    }

    // Summary details
    document.getElementById('meta-fir-no').textContent = res.fir_number || 'N/A';
    document.getElementById('meta-ps').textContent = res.police_station || 'N/A';
    document.getElementById('meta-category').textContent = (res.topic || 'N/A').replace(/_/g, ' ').toUpperCase();
    document.getElementById('meta-time').textContent = `${elapsed.toFixed(2)}s`;

    // Risk badge styling
    const riskBadge = document.getElementById('meta-risk');
    const riskLevel = res.risk_level || 'Medium';
    riskBadge.textContent = `Risk: ${riskLevel}`;
    riskBadge.className = 'badge';
    if (riskLevel === 'High') { riskBadge.classList.add('bg-danger'); }
    else if (riskLevel === 'Low') { riskBadge.classList.add('bg-success'); }
    else { riskBadge.classList.add('bg-warning', 'text-dark'); }

    // Parties
    document.getElementById('info-complainant').textContent = res.complainant || 'N/A';
    document.getElementById('info-accused').textContent = res.accused || 'N/A';
    
    const sectionsList = res.sections || [];
    document.getElementById('info-sections').textContent = sectionsList.length > 0 ? sectionsList.join(', ') : 'None identified';

    // Renders AI Advisory Report
    document.getElementById('fir-advice-content').innerHTML = parseMarkdown(res.legal_advice);

    // Precedents
    const precedentsContainer = document.getElementById('fir-precedents-content');
    precedentsContainer.innerHTML = '';
    const precedents = res.precedents || [];
    if (precedents.length > 0) {
        precedents.forEach((caseItem, idx) => {
            const div = document.createElement('div');
            div.className = 'accordion-item bg-dark border-secondary mb-2';
            const caseName = caseItem.case_name || caseItem.citation || `Case #${idx + 1}`;
            const similarity = ((caseItem.similarity || caseItem.score || 0) * 100).toFixed(1);
            
            div.innerHTML = `
                <h2 class="accordion-header" id="heading-fir-prec-${idx}">
                    <button class="accordion-button collapsed bg-dark text-warning border-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-fir-prec-${idx}">
                        <strong>${caseName} (${caseItem.year || 'N/A'})</strong> - [Match: ${similarity}%]
                    </button>
                </h2>
                <div id="collapse-fir-prec-${idx}" class="accordion-collapse collapse" data-bs-parent="#fir-precedents-content">
                    <div class="accordion-body text-light">
                        <p class="mb-1"><strong>Court:</strong> <span class="text-muted">${caseItem.court || 'N/A'}</span></p>
                        <p class="mb-1"><strong>Facts:</strong></p><p class="text-muted">${caseItem.facts || 'N/A'}</p>
                        <p class="mb-1"><strong>Decision:</strong></p><p class="text-muted">${caseItem.holding || 'N/A'}</p>
                    </div>
                </div>
            `;
            precedentsContainer.appendChild(div);
        });
    } else {
        precedentsContainer.innerHTML = '<div class="alert alert-info bg-dark border-secondary text-info">No relevant case precedents retrieved.</div>';
    }

    // Extracted Text
    document.getElementById('fir-extracted-text').textContent = res.extracted_text || 'No text extracted.';
    
    // Performance Timing
    document.getElementById('fir-raw-perf').textContent = JSON.stringify(res.performance || {}, null, 2);
}

async function handleFIRContextualChat(e) {
    e.preventDefault();
    const chatInput = document.getElementById('fir-ctx-chat-input');
    if (!chatInput || !chatInput.value.trim() || !activeFIRText) return;

    const question = chatInput.value.trim();
    chatInput.value = '';

    const chatMessages = document.getElementById('fir-ctx-chat-messages');
    
    // Render user bubble
    const userDiv = document.createElement('div');
    userDiv.className = 'message-bubble user';
    userDiv.textContent = question;
    chatMessages.appendChild(userDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Append to local history
    firChatHistory.push({ role: 'user', content: question });

    // Render loading indicator
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message-bubble assistant';
    loadingDiv.innerHTML = `
        <div class="typing-indicator">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
        </div>
    `;
    chatMessages.appendChild(loadingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const data = await fetchWithAuth('/api/chat-fir', {
            method: 'POST',
            body: JSON.stringify({
                text: activeFIRText,
                question: question,
                history: firChatHistory
            })
        });

        // Remove loading indicator
        chatMessages.removeChild(loadingDiv);

        // Render AI bubble
        const aiDiv = document.createElement('div');
        aiDiv.className = 'message-bubble assistant';
        aiDiv.innerHTML = parseMarkdown(data.response);
        chatMessages.appendChild(aiDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // Append to history
        firChatHistory.push({ role: 'assistant', content: data.response });
    } catch (err) {
        chatMessages.removeChild(loadingDiv);
        const errDiv = document.createElement('div');
        errDiv.className = 'message-bubble assistant text-danger';
        errDiv.textContent = `Error: ${err.message}`;
        chatMessages.appendChild(errDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}
