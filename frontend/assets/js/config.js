// Configuración dinámica del entorno Bar Mune
// En desarrollo local con servidor estático (puerto 3000/5500): apunta a http://localhost:5000
// En producción (Railway / Docker / Flask): usa URLs relativas para evitar problemas de CORS y SSL
(function() {
    const isSeparateLocalPort = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && 
        (window.location.port === '3000' || window.location.port === '5500');
    window.API_BASE = isSeparateLocalPort ? 'http://localhost:5000' : '';
})();
