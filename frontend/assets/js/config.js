// Dynamic Environment, Theme Manager (Light Default + High-Contrast Toggle) & English Helpers - Bar Mune POS
(function() {
    const isSeparateLocalPort = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && 
        (window.location.port === '3000' || window.location.port === '5500');
    window.API_BASE = isSeparateLocalPort ? 'http://localhost:5000' : '';

    // --- 1. THEME MANAGER (Default: High-Contrast Light Theme) ---
    const THEME_KEY = 'barmune_theme';

    function getTheme() {
        const stored = localStorage.getItem(THEME_KEY);
        return (stored === 'dark' || stored === 'light') ? stored : 'light';
    }

    function applyTheme(theme) {
        const root = document.documentElement;
        if (theme === 'dark') {
            root.classList.add('theme-dark');
            root.classList.remove('theme-light');
        } else {
            root.classList.add('theme-light');
            root.classList.remove('theme-dark');
        }
        localStorage.setItem(THEME_KEY, theme);
        updateThemeUI(theme);
    }

    function updateThemeUI(theme) {
        // Update theme toggle button labels & icons
        document.querySelectorAll('.theme-toggle-btn').forEach(btn => {
            if (theme === 'dark') {
                btn.innerHTML = `
                    <svg class="w-4 h-4 text-amber-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>
                    </svg>
                    <span class="hidden sm:inline">Light Theme</span>
                `;
                btn.title = 'Switch to High-Contrast Light Theme';
            } else {
                btn.innerHTML = `
                    <svg class="w-4 h-4 text-slate-700 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>
                    </svg>
                    <span class="hidden sm:inline">Dark Theme</span>
                `;
                btn.title = 'Switch to High-Contrast Dark Theme';
            }
        });

        // Swap logos automatically for optimal contrast (except printable invoice logo)
        document.querySelectorAll('img[alt="Bar Mune"]').forEach(img => {
            if (img.id === 'factura-logo') return;
            const src = img.getAttribute('src') || '';
            if (src.includes('Isotipo')) return;
            const prefix = src.startsWith('../') ? '../assets/Logos/' : './assets/Logos/';
            if (theme === 'dark') {
                img.setAttribute('src', prefix + 'Horizontal_Fondo_Transparente_Positivo.png');
            } else {
                img.setAttribute('src', prefix + 'Horizontal_Fondo_Transparente_Negativo.png');
            }
        });
    }

    window.toggleTheme = function() {
        const next = getTheme() === 'dark' ? 'light' : 'dark';
        applyTheme(next);
    };

    window.getTheme = getTheme;

    // Apply immediately before DOM paint
    applyTheme(getTheme());

    // --- 2. ENGLISH TRANSLATION HELPERS FOR DB VALUES ---
    const ROLE_MAP = {
        'admin': 'Administrator',
        'administrador': 'Administrator',
        'cajero': 'Cashier',
        'mesero': 'Waiter'
    };

    const STATUS_MAP = {
        'abierta': 'Open',
        'en_proceso': 'In Progress',
        'en proceso': 'In Progress',
        'lista': 'Ready to Pay',
        'pagada': 'Paid',
        'cancelada': 'Cancelled',
        'activo': 'Active',
        'activa': 'Active',
        'inactivo': 'Inactive',
        'inactiva': 'Inactive',
        'agotado': 'Out of Stock',
        'libre': 'Available'
    };

    const METHOD_MAP = {
        'efectivo': 'Cash',
        'tarjeta': 'Card',
        'transferencia': 'Transfer'
    };

    window.tRole = function(rol) {
        if (!rol) return 'No Role';
        const key = String(rol).trim().toLowerCase();
        return ROLE_MAP[key] || rol;
    };

    window.tStatus = function(status) {
        if (!status) return '';
        const key = String(status).trim().toLowerCase();
        return STATUS_MAP[key] || status;
    };

    window.tMethod = function(method) {
        if (!method) return '';
        const key = String(method).trim().toLowerCase();
        return METHOD_MAP[key] || method;
    };

    document.addEventListener('DOMContentLoaded', () => {
        applyTheme(getTheme());
        // Translate role badges in sidebar/header after page scripts run
        setTimeout(() => {
            document.querySelectorAll('#user-rol, .user-display-rol').forEach(el => {
                if (el.textContent) {
                    el.textContent = window.tRole(el.textContent);
                }
            });
        }, 10);
    });
})();
