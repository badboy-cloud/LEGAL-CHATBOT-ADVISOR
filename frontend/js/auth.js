// auth.js - Session validation and login logic

document.addEventListener('DOMContentLoaded', () => {
    // Skip verification check on login page
    if (window.location.pathname.includes('login.html')) {
        return;
    }
    checkAuthentication();
    updateUIForUserRole();
});

function checkAuthentication() {
    const token = localStorage.getItem('jwt_token');
    if (!token) {
        window.location.href = 'login.html';
    }
}

function updateUIForUserRole() {
    const username = localStorage.getItem('username') || 'User';
    const role = localStorage.getItem('role') || 'User';
    
    // Update Profile Labels in UI
    const usernameEl = document.getElementById('user-profile-name');
    const roleEl = document.getElementById('user-profile-role');
    if (usernameEl) usernameEl.textContent = username;
    if (roleEl) roleEl.textContent = role;

    // Show/Hide Admin menu options
    const adminMenuOption = document.getElementById('admin-dashboard-link');
    if (adminMenuOption) {
        if (role === 'Admin') {
            adminMenuOption.style.display = 'block';
        } else {
            adminMenuOption.style.display = 'none';
        }
    }
}

async function login(username, password) {
    try {
        const data = await fetchWithAuth('/api/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
        
        localStorage.setItem('jwt_token', data.access_token);
        localStorage.setItem('username', data.username);
        localStorage.setItem('role', data.role);
        
        window.location.href = 'dashboard.html';
        return { success: true };
    } catch (err) {
        return { success: false, error: err.message };
    }
}

async function register(username, password, role) {
    try {
        await fetchWithAuth('/api/register', {
            method: 'POST',
            body: JSON.stringify({ username, password, role })
        });
        return { success: true };
    } catch (err) {
        return { success: false, error: err.message };
    }
}

function logout() {
    localStorage.removeItem('jwt_token');
    localStorage.removeItem('username');
    localStorage.removeItem('role');
    window.location.href = 'login.html';
}
