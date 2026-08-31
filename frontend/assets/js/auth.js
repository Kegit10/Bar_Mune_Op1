const auth = {
    async login(email, password) {
        const response = await window.api.post('/api/auth/login', { email, password });
        // La API devuelve: { success: true, data: { access_token, user } }
        if (response && response.success && response.data && response.data.access_token) {
            const user = response.data.user || {};
            // Normalizar rol
            user.rol = user.rol_nombre || user.rol || '';
            localStorage.setItem('barmune_token', response.data.access_token);
            localStorage.setItem('barmune_user', JSON.stringify(user));
            return true;
        }
        const msg = response?.message || 'Credenciales inválidas';
        throw new Error(msg);
    },

    logout() {
        localStorage.removeItem('barmune_token');
        localStorage.removeItem('barmune_user');
        const base = window.location.pathname.includes('/pages/') 
            ? '../index.html' 
            : './index.html';
        window.location.href = base;
    },

    getUser() {
        try {
            const userStr = localStorage.getItem('barmune_user');
            if (!userStr) return null;
            const user = JSON.parse(userStr);
            if (user && !user.rol && user.rol_nombre) {
                user.rol = user.rol_nombre;
            }
            return user;
        } catch {
            return null;
        }
    },

    getRole() {
        const user = this.getUser();
        return (user?.rol || user?.rol_nombre || '').toLowerCase();
    },

    getToken() {
        return localStorage.getItem('barmune_token');
    },

    isAuthenticated() {
        return !!localStorage.getItem('barmune_token');
    },

    hasRole(...roles) {
        const user = this.getUser();
        if (!user) return false;
        const rolNombre = (user.rol_nombre || user.rol || '').toLowerCase();
        const allowed = roles.map(r => String(r).toLowerCase());
        return allowed.includes(rolNombre);
    },

    checkAuth() {
        const onLoginPage = window.location.pathname.endsWith('index.html') 
            || window.location.pathname === '/' 
            || window.location.pathname.endsWith('/');
        if (!this.isAuthenticated() && !onLoginPage) {
            window.location.href = '../index.html';
        }
    }
};

window.auth = auth;

// Guard: en páginas que NO son el login, verificar autenticación
document.addEventListener('DOMContentLoaded', () => {
    const onLoginPage = window.location.pathname.endsWith('index.html')
        || window.location.pathname === '/'
        || window.location.pathname.endsWith('/');
    if (!onLoginPage) {
        auth.checkAuth();
    }
});
