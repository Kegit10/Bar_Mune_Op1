class Api {
    constructor() {
        this.baseUrl = window.API_BASE || 'http://localhost:5000';
    }

    async request(path, options = {}) {
        const token = localStorage.getItem('barmune_token');
        const headers = {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
            ...(options.headers || {})
        };

        const config = { ...options, headers };

        try {
            const response = await fetch(`${this.baseUrl}${path}`, config);

            if (response.status === 401) {
                localStorage.removeItem('barmune_token');
                localStorage.removeItem('barmune_user');
                const onPages = window.location.pathname.includes('/pages/');
                window.location.href = onPages ? '../index.html' : './index.html';
                return null;
            }

            const data = await response.json().catch(() => null);

            if (!response.ok) {
                throw new Error(data?.message || `Error ${response.status}`);
            }

            return data;
        } catch (error) {
            // No re-lanzar errores de redirección
            if (error.name !== 'AbortError') {
                console.error('API Error:', path, error.message);
            }
            throw error;
        }
    }

    get(path) {
        return this.request(path, { method: 'GET' });
    }

    post(path, data) {
        return this.request(path, { method: 'POST', body: JSON.stringify(data) });
    }

    put(path, data) {
        return this.request(path, { method: 'PUT', body: JSON.stringify(data) });
    }

    patch(path, data) {
        return this.request(path, { method: 'PATCH', body: JSON.stringify(data) });
    }

    delete(path) {
        return this.request(path, { method: 'DELETE' });
    }
}

window.api = new Api();
