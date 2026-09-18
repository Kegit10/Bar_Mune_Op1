/**
 * perfil.js - Visualización de Perfil de Usuario ("Mi Perfil")
 * Permite a cualquier usuario consultar sus datos personales y sede asignada en solo lectura.
 */

(function() {
    function injectPerfilModal() {
        if (document.getElementById('perfil-modal-overlay')) return;

        const modalHtml = `
        <div id="perfil-modal-overlay" class="fixed inset-0 z-50 overflow-y-auto bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4" style="display: none;">
            <div class="relative w-full max-w-md bg-[#0E1526] border border-[#222E46] rounded-2xl shadow-2xl overflow-hidden transition-all">
                
                <!-- Encabezado con degradado suave Bar Mune / Luné -->
                <div class="relative bg-gradient-to-r from-[#141C2E] to-[#1E293B] border-b border-[#222E46] px-6 py-5 flex items-center justify-between">
                    <div class="flex items-center gap-3.5">
                        <div class="w-11 h-11 rounded-xl bg-gradient-to-tr from-amber-500 to-purple-600 p-0.5 shadow-md flex items-center justify-center">
                            <div class="w-full h-full bg-[#0E1526] rounded-[10px] flex items-center justify-center text-white font-bold text-lg" id="perfil-avatar-initials">
                                U
                            </div>
                        </div>
                        <div>
                            <h3 class="text-lg font-bold text-white tracking-tight flex items-center gap-2">
                                Mi Perfil
                                <span class="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-green-500/15 text-green-400 border border-green-500/30" id="perfil-tag-estado">
                                    Activo
                                </span>
                            </h3>
                            <p class="text-xs text-slate-400">Datos personales y permisos</p>
                        </div>
                    </div>
                    <button id="btn-cerrar-perfil" class="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors" title="Cerrar">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                    </button>
                </div>

                <!-- Cuerpo de datos en Solo Lectura -->
                <div class="p-6 space-y-3.5 text-sm">
                    
                    <!-- Nombre Completo -->
                    <div class="bg-[#141C2E] border border-[#222E46] rounded-xl p-3">
                        <span class="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">Nombre Completo</span>
                        <span class="text-white font-medium break-words text-sm" id="perfil-nombre-completo">-</span>
                    </div>

                    <!-- Correo Electrónico -->
                    <div class="bg-[#141C2E] border border-[#222E46] rounded-xl p-3">
                        <span class="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">Correo Electrónico</span>
                        <div class="flex items-center gap-2 text-slate-200 font-medium break-all">
                            <svg class="w-4 h-4 text-amber-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.206"/></svg>
                            <span id="perfil-email">-</span>
                        </div>
                    </div>

                    <!-- Teléfono y Rol -->
                    <div class="grid grid-cols-2 gap-3">
                        <div class="bg-[#141C2E] border border-[#222E46] rounded-xl p-3">
                            <span class="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">Teléfono</span>
                            <div class="flex items-center gap-1.5 text-white font-medium text-xs sm:text-sm">
                                <svg class="w-3.5 h-3.5 text-slate-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/></svg>
                                <span id="perfil-telefono">No registrado</span>
                            </div>
                        </div>

                        <div class="bg-[#141C2E] border border-[#222E46] rounded-xl p-3">
                            <span class="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">Rol / Permisos</span>
                            <div class="flex items-center gap-1.5 text-amber-400 font-bold capitalize text-xs sm:text-sm">
                                <svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>
                                <span id="perfil-rol">-</span>
                            </div>
                        </div>
                    </div>

                    <!-- Sede Asignada -->
                    <div class="bg-[#141C2E] border border-[#222E46] rounded-xl p-3">
                        <div class="flex items-center justify-between mb-1">
                            <span class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Sede Asignada</span>
                        </div>
                        <div class="flex items-center gap-2 text-white font-medium">
                            <svg class="w-4 h-4 text-purple-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>
                            <span id="perfil-sede" class="text-purple-300 font-semibold">Sin sede asignada</span>
                        </div>
                    </div>

                    <!-- Nota Informativa Solo Lectura -->
                    <div class="p-3 rounded-xl bg-slate-800/50 border border-slate-700/50 text-[11px] text-slate-400 flex items-center gap-2">
                        <svg class="w-4 h-4 text-slate-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                        <span>Información de solo lectura. Para cambios, contacta al administrador.</span>
                    </div>
                </div>

                <!-- Footer -->
                <div class="bg-[#141C2E]/90 border-t border-[#222E46] px-6 py-3.5 flex justify-end">
                    <button id="btn-entendido-perfil" class="px-5 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold transition-colors shadow-sm">
                        Cerrar
                    </button>
                </div>
            </div>
        </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        const overlay = document.getElementById('perfil-modal-overlay');
        document.getElementById('btn-cerrar-perfil')?.addEventListener('click', closePerfilModal);
        document.getElementById('btn-entendido-perfil')?.addEventListener('click', closePerfilModal);
        overlay?.addEventListener('click', (e) => {
            if (e.target === overlay) closePerfilModal();
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closePerfilModal();
        });
    }

    async function openPerfilModal() {
        injectPerfilModal();
        const overlay = document.getElementById('perfil-modal-overlay');
        if (!overlay) return;

        let user = window.auth?.getUser() || {};
        renderUserData(user);
        overlay.style.display = 'flex';

        try {
            if (window.api && typeof window.api.get === 'function') {
                const res = await window.api.get('/api/auth/me');
                if (res?.data) {
                    user = { ...user, ...res.data };
                    localStorage.setItem('barmune_user', JSON.stringify(user));
                    renderUserData(user);
                }
            }
        } catch (e) {
            console.warn('Usando datos de sesión local:', e.message);
        }
    }

    function renderUserData(user) {
        const nombre = (user.nombre || '').trim();
        const apellido = (user.apellido || '').trim();
        const nombreCompleto = `${nombre} ${apellido}`.trim() || 'Usuario';
        const iniciales = (nombre.charAt(0) + (apellido.charAt(0) || '')).toUpperCase() || 'U';

        const elInitials = document.getElementById('perfil-avatar-initials');
        if (elInitials) elInitials.textContent = iniciales;

        const elNombreCompleto = document.getElementById('perfil-nombre-completo');
        if (elNombreCompleto) elNombreCompleto.textContent = nombreCompleto;

        const elEmail = document.getElementById('perfil-email');
        if (elEmail) elEmail.textContent = user.email || '-';

        const elTel = document.getElementById('perfil-telefono');
        if (elTel) elTel.textContent = user.telefono ? user.telefono : 'No registrado';

        const elRol = document.getElementById('perfil-rol');
        if (elRol) elRol.textContent = user.rol_nombre || user.rol || 'Sin rol';

        const elSede = document.getElementById('perfil-sede');
        if (elSede) {
            elSede.textContent = (user.sede_nombre && user.sede_nombre.trim()) ? user.sede_nombre : 'Sin sede asignada';
        }

        const elEstado = document.getElementById('perfil-tag-estado');
        if (elEstado) {
            const estado = (user.estado || 'activo').toLowerCase();
            elEstado.textContent = estado.charAt(0).toUpperCase() + estado.slice(1);
            if (estado === 'activo') {
                elEstado.className = 'px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-green-500/15 text-green-400 border border-green-500/30';
            } else {
                elEstado.className = 'px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-amber-500/15 text-amber-400 border border-amber-500/30';
            }
        }
    }

    function closePerfilModal() {
        const overlay = document.getElementById('perfil-modal-overlay');
        if (overlay) overlay.style.display = 'none';
    }

    window.openPerfilModal = openPerfilModal;
    window.closePerfilModal = closePerfilModal;

    function bindUserClick() {
        injectPerfilModal();
        document.querySelectorAll('#user-name, .user-display-name, .user-display-container, [data-action="open-profile"]').forEach(el => {
            el.style.cursor = 'pointer';
            el.setAttribute('title', 'Ver mi perfil');
            el.onclick = (e) => {
                e.preventDefault();
                openPerfilModal();
            };
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bindUserClick);
    } else {
        bindUserClick();
    }
})();
