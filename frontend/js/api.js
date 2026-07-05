// api.js - API Client and Fetch Wrappers
const API_BASE_URL = localStorage.getItem('api_base_url') || 'http://127.0.0.1:8000';
const DEFAULT_TIMEOUT = 600000; // 10 minutes timeout for LLM reasoning

async function fetchWithAuth(endpoint, options = {}) {
    const token = localStorage.getItem('jwt_token');
    
    // Setup Headers
    options.headers = {
        ...options.headers,
    };
    
    if (token) {
        options.headers['Authorization'] = `Bearer ${token}`;
    }
    
    if (options.body && !(options.body instanceof FormData)) {
        options.headers['Content-Type'] = 'application/json';
    }

    // Handle Timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), options.timeout || DEFAULT_TIMEOUT);
    options.signal = controller.signal;

    try {
        const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
        const response = await fetch(url, options);
        clearTimeout(timeoutId);

        // JWT token expired or unauthorized
        if (response.status === 401) {
            localStorage.removeItem('jwt_token');
            localStorage.removeItem('username');
            localStorage.removeItem('role');
            window.location.href = 'login.html?expired=true';
            throw new Error('Session expired. Please log in again.');
        }

        // Rate Limited
        if (response.status === 429) {
            throw new Error('Rate limit exceeded. Maximum 20 requests per minute allowed.');
        }

        if (!response.ok) {
            const errData = await response.json().catch(() => ({ detail: 'Unknown API error' }));
            throw new Error(errData.detail || `Server returned status ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
            throw new Error('Request timed out. The model took too long to respond.');
        }
        throw error;
    }
}
