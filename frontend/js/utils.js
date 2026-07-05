// utils.js - Shared utilities, file validations, and UI alert helpers

// Simple Markdown to HTML parser
function parseMarkdown(text) {
    if (!text) return '';
    let html = text.trim();

    // Escape HTML tags to prevent XSS
    html = html
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // Headers
    html = html.replace(/^### (.*?)$/gm, '<h5 class="text-warning mt-3">$1</h5>');
    html = html.replace(/^## (.*?)$/gm, '<h4 class="text-warning mt-4">$1</h4>');
    html = html.replace(/^# (.*?)$/gm, '<h3 class="text-warning mt-4">$1</h3>');

    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Bullet points
    html = html.replace(/^\s*-\s+(.*?)$/gm, '<li>$1</li>');
    // Wrap lists
    html = html.replace(/(<li>.*?<\/li>)/gs, '<ul class="mb-3">$1</ul>');
    // Clean duplicate list tags
    html = html.replace(/<\/ul>\s*<ul class="mb-3">/g, '');

    // Paragraphs / Newlines
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');

    // Wrap in paragraph if not already block
    if (!html.startsWith('<h') && !html.startsWith('<ul') && !html.startsWith('<p')) {
        html = '<p>' + html + '</p>';
    }

    return html;
}

// File Validation Helper
function validateFile(file) {
    const allowedExtensions = ['.pdf', '.jpg', '.jpeg', '.png'];
    const maxBytes = 10 * 1024 * 1024; // 10MB
    
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowedExtensions.includes(ext)) {
        return { valid: false, error: 'Unsupported file format. Only PDF, JPG, JPEG, PNG are supported.' };
    }
    
    if (file.size > maxBytes) {
        return { valid: false, error: 'File size exceeds maximum allowed size of 10MB.' };
    }
    
    return { valid: true };
}

// Alert rendering utilities
function showAlert(containerId, message, type = 'danger') {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show d-flex align-items-center" role="alert">
            <i class="fa-solid ${type === 'danger' ? 'fa-circle-exclamation' : 'fa-circle-check'} me-2"></i>
            <div>${message}</div>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
}

// Date formatter
function formatTimestamp(isoString) {
    if (!isoString) return 'N/A';
    try {
        const d = new Date(isoString);
        return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
        return isoString;
    }
}
