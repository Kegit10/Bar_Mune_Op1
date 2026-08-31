const auth = {
    async login(email, password) {
        const response = await window.api.post('/api/auth/login', { email, password });
        // La API devuelve: { success: true, data: { access_token, user } }
        if (response && response.success && response.data && response.data.access_token) {
            localStorage.setItem('barmune_token', response.data.access_token);
            localStorage.setItem('barmune_user', JSON.stringify(response.data.user));
            return true;
        }
        const msg = response?.message || 'Credenciales inválidas';
        throw new Error(msg);
    },

    logout() {
        localStorage.removeItem('barmune_token');
        localStorage.removeItem('barmune_user');
        // Navegar a index.html relativo a la raíz del servidor
        const base = window.location.pathname.includes('/pages/') 
            ? '../index.html' 
            : './index.html';
        window.location.href = base;
    },

    getUser() {
        try {
            const user = localStorage.getItem('barmune_user');
            return user ? JSON.parse(user) : null;
        } catch { return null; }
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
        // El rol puede estar en user.rol o user.roles.nombre
        const rolNombre = user.rol_nombre || (user.roles && user.roles.nombre) || user.rol || '';
        return roles.includes(rolNombre.toLowerCase());
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
