// profile.js - Handles profile views and credentials management

document.addEventListener('DOMContentLoaded', () => {
    if (!window.location.pathname.includes('profile.html')) return;
    loadProfileDetails();
    
    const form = document.getElementById('change-password-form');
    if (form) {
        form.addEventListener('submit', handleChangePassword);
    }
});

function loadProfileDetails() {
    const username = localStorage.getItem('username') || 'Jane Doe';
    const role = localStorage.getItem('role') || 'User';
    
    document.getElementById('profile-username').value = username;
    document.getElementById('profile-email').value = `${username.toLowerCase().replace(/\s/g, '')}@legaladvisor.org`;
    document.getElementById('profile-role-badge').textContent = role;
}

async function handleChangePassword(e) {
    e.preventDefault();
    const oldPass = document.getElementById('old-password').value;
    const newPass = document.getElementById('new-password').value;
    const confirmPass = document.getElementById('confirm-password').value;

    if (!oldPass || !newPass || !confirmPass) {
        showAlert('profile-alert-container', 'All password fields are required.', 'danger');
        return;
    }

    if (newPass !== confirmPass) {
        showAlert('profile-alert-container', 'New passwords do not match!', 'danger');
        return;
    }

    if (newPass.length < 6) {
        showAlert('profile-alert-container', 'New password must be at least 6 characters.', 'danger');
        return;
    }

    // Since we do not have an explicit change password API endpoint in routes.py, 
    // we mock the success or display details as an extension stub.
    // This maintains backend parity without rewriting backend APIs.
    showAlert('profile-alert-container', 'Password updated successfully! (Mocked implementation)', 'success');
    document.getElementById('change-password-form').reset();
}
