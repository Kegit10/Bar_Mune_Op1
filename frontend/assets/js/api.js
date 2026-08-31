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

    async download(path, fallbackFilename = 'reporte') {
        const token = localStorage.getItem('barmune_token');
        const headers = {
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        };

        try {
            const response = await fetch(`${this.baseUrl}${path}`, { method: 'GET', headers });

            if (response.status === 401) {
                localStorage.removeItem('barmune_token');
                localStorage.removeItem('barmune_user');
                const onPages = window.location.pathname.includes('/pages/');
                window.location.href = onPages ? '../index.html' : './index.html';
                return;
            }

            if (!response.ok) {
                const errData = await response.json().catch(() => null);
                throw new Error(errData?.message || `Error en la descarga (${response.status})`);
            }

            // Extraer nombre de archivo si viene en content-disposition
            let filename = fallbackFilename;
            const disposition = response.headers.get('Content-Disposition');
            if (disposition && disposition.includes('filename=')) {
                const match = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (match && match[1]) {
                    filename = match[1].replace(/['"]/g, '');
                }
            }

            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(downloadUrl);
        } catch (error) {
            console.error('Download Error:', error);
            throw error;
        }
    }
}

window.api = new Api();
