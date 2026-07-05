// settings.js - Manages API overrides and theme configurations

document.addEventListener('DOMContentLoaded', () => {
    if (!window.location.pathname.includes('settings.html')) return;
    loadSettings();

    const form = document.getElementById('settings-form');
    if (form) {
        form.addEventListener('submit', handleSettingsSave);
    }
});

function loadSettings() {
    const url = localStorage.getItem('api_base_url') || 'http://127.0.0.1:8000';
    const fontSize = localStorage.getItem('font_size') || 'normal';
    
    document.getElementById('api-url-input').value = url;
    document.getElementById('font-size-select').value = fontSize;
}

function handleSettingsSave(e) {
    e.preventDefault();
    
    const url = document.getElementById('api-url-input').value.trim();
    const fontSize = document.getElementById('font-size-select').value;
    
    localStorage.setItem('api_base_url', url);
    localStorage.setItem('font_size', fontSize);
    
    showAlert('settings-alert-container', 'Configuration settings saved successfully! Reloading...', 'success');
    setTimeout(() => {
        window.location.reload();
    }, 1000);
}

function clearLocalCache() {
    localStorage.removeItem('query_results');
    localStorage.removeItem('fir_results');
    localStorage.removeItem('notice_results');
    showAlert('settings-alert-container', 'Local analysis caches cleared successfully!', 'success');
}
