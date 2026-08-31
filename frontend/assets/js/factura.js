/**
 * factura.js - Módulo de Visualización, Impresión y Descarga PDF de Factura Electrónica de Venta
 * Bar Mune POS
 */

(function() {
    // Inyectar librería html2pdf.js si no existe
    if (!window.html2pdf) {
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js';
        script.integrity = 'sha512-GsLlZN/3F2ErC5ifS5QtgpiJtWd43JWSuIgh7mbzZ8zBps+dvLusV+eNQATqgA/HdeKFVgA5v3S/cIrLF7QnIg==';
        script.crossOrigin = 'anonymous';
        script.referrerPolicy = 'no-referrer';
        document.head.appendChild(script);
    }

    // Modal container HTML
    const modalHtml = `
    <div id="factura-modal-overlay" class="fixed inset-0 z-50 overflow-y-auto bg-slate-900/80 backdrop-blur-sm flex items-center justify-center p-4" style="display: none;">
        <div class="bg-white text-slate-900 rounded-2xl shadow-2xl max-w-2xl w-full overflow-hidden flex flex-col max-h-[92vh] border border-slate-200">
            <!-- Modal Actions Top Bar -->
            <div class="bg-slate-100 px-6 py-3 border-b border-slate-200 flex justify-between items-center no-print">
                <span class="text-xs font-bold text-slate-600 uppercase tracking-wider flex items-center gap-1.5">
                    <svg class="w-4 h-4 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                    Factura Electrónica de Venta
                </span>
                <div class="flex items-center gap-2">
                    <button id="btn-descargar-pdf" class="px-3.5 py-1.5 bg-gradient-to-r from-[#2A40FF] to-[#7C3AED] hover:from-[#3B52FF] hover:to-[#8B5CF6] text-white rounded-lg font-semibold text-xs transition-all flex items-center gap-1.5 shadow-sm">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
                        <span>Descargar PDF</span>
                    </button>
                    <button id="btn-imprimir-factura" class="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-900 text-white rounded-lg font-semibold text-xs transition-colors flex items-center gap-1.5 shadow-sm">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>
                        <span>Imprimir</span>
                    </button>
                    <button id="btn-cerrar-factura" class="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-200 transition-colors">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                    </button>
                </div>
            </div>

            <!-- Invoice Document Printable Area -->
            <div id="factura-print-area" class="p-8 overflow-y-auto font-sans text-xs bg-white text-slate-900 leading-relaxed">
                <!-- Header -->
                <div class="flex justify-between items-start border-b-2 border-slate-900 pb-5 mb-5">
                    <div class="space-y-1">
                        <img id="factura-logo" src="../assets/Logos/Horizontal_Fondo_Transparente_Positivo.png" onerror="this.src='../assets/Logos/Horizontal_Fondo_Transparente_Positivo'" alt="Bar Mune" class="h-10 w-auto mb-2 object-contain" />
                        <h2 class="text-base font-bold uppercase tracking-wide text-slate-900" id="factura-emisor-razon">Bar Luné S.A.S.</h2>
                        <p class="text-slate-600 font-mono font-medium">NIT: <span id="factura-emisor-nit">900.123.456-7</span></p>
                        <p class="text-slate-600">Sede: <strong id="factura-sede-nombre" class="text-slate-800">Restrepo</strong></p>
                        <p class="text-slate-600">Dirección: <span id="factura-sede-dir">Calle 15 # 22-30</span> • <span id="factura-sede-ciudad">Villavicencio</span></p>
                        <p class="text-slate-600">Teléfono: <span id="factura-sede-tel">(+57) 310 000 0000</span></p>
                    </div>

                    <div class="text-right bg-slate-50 p-4 rounded-xl border border-slate-200 min-w-[220px]">
                        <span class="inline-block px-2 py-0.5 bg-amber-500/20 text-amber-800 text-[10px] font-bold uppercase tracking-wider rounded mb-1">Documento Oficial</span>
                        <h1 class="text-sm font-extrabold text-slate-900 uppercase tracking-tight">FACTURA ELECTRÓNICA DE VENTA</h1>
                        <p class="text-sm font-bold font-mono text-amber-600 mt-1" id="factura-numero">BM-20260831-XXXXXX</p>
                        <div class="text-[11px] text-slate-500 mt-2 space-y-0.5">
                            <p>Fecha: <strong id="factura-fecha" class="text-slate-700">2026-08-31</strong></p>
                            <p>Hora: <strong id="factura-hora" class="text-slate-700">20:45:00</strong></p>
                        </div>
                    </div>
                </div>

                <!-- Customer & Order Metadata -->
                <div class="grid grid-cols-2 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200 mb-5">
                    <div>
                        <p class="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">Datos del Adquirente / Cliente</p>
                        <p class="font-bold text-sm text-slate-900" id="factura-cliente-nombre">Consumidor Final</p>
                        <p class="text-slate-600 font-mono">CC / NIT: <span id="factura-cliente-doc" class="font-bold">222222222222</span></p>
                        <p class="text-slate-500 text-[11px]" id="factura-cliente-contacto"></p>
                    </div>
                    <div class="border-l border-slate-200 pl-4 space-y-0.5">
                        <p class="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">Datos del Servicio</p>
                        <p class="text-slate-700">Ubicación: <strong id="factura-mesa" class="text-slate-900">Mesa 1</strong></p>
                        <p class="text-slate-700">Mesero: <span id="factura-mesero">Admin Sistema</span></p>
                        <p class="text-slate-700">Cajero: <span id="factura-cajero">Admin Sistema</span></p>
                        <p class="text-slate-700">Método de Pago: <strong id="factura-metodo" class="uppercase text-amber-700 font-bold">EFECTIVO</strong></p>
                    </div>
                </div>

                <!-- Detalle del Consumo Table -->
                <div class="mb-5 border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                    <table class="w-full text-left">
                        <thead class="bg-slate-900 text-white font-semibold text-[11px] uppercase tracking-wider">
                            <tr>
                                <th class="py-2.5 px-3 text-center w-12">Cant.</th>
                                <th class="py-2.5 px-3">Descripción</th>
                                <th class="py-2.5 px-3 text-right">Vr. Unitario</th>
                                <th class="py-2.5 px-3 text-right">Impuesto (IVA)</th>
                                <th class="py-2.5 px-3 text-right">Total</th>
                            </tr>
                        </thead>
                        <tbody id="factura-items-tbody" class="divide-y divide-slate-200 text-[11px]">
                            <!-- Inyectado dinámicamente -->
                        </tbody>
                    </table>
                </div>

                <!-- Totals & Summary -->
                <div class="flex justify-end mb-6">
                    <div class="w-72 bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-1.5 text-xs">
                        <div class="flex justify-between text-slate-600">
                            <span>Subtotal (Base Gravable):</span>
                            <span id="factura-subtotal" class="font-mono font-medium">$ 0</span>
                        </div>
                        <div class="flex justify-between text-slate-600">
                            <span>IVA (19%):</span>
                            <span id="factura-impuesto" class="font-mono font-medium">$ 0</span>
                        </div>
                        <div class="flex justify-between text-slate-600" id="factura-propina-row">
                            <span>Propina Voluntaria:</span>
                            <span id="factura-propina" class="font-mono font-medium">$ 0</span>
                        </div>
                        <div class="flex justify-between text-sm font-extrabold text-slate-900 pt-2 border-t-2 border-slate-300">
                            <span>TOTAL FACTURA:</span>
                            <span id="factura-total" class="text-amber-600 font-mono">$ 0</span>
                        </div>
                        <div class="flex justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-200" id="factura-recibido-row">
                            <span>Monto Recibido:</span>
                            <span id="factura-recibido" class="font-mono">$ 0</span>
                        </div>
                        <div class="flex justify-between text-[11px] text-slate-500" id="factura-cambio-row">
                            <span>Cambio:</span>
                            <span id="factura-cambio" class="font-mono text-green-700 font-semibold">$ 0</span>
                        </div>
                    </div>
                </div>

                <!-- Footer Legal DIAN -->
                <div class="border-t border-dashed border-slate-300 pt-4 text-center text-[10px] text-slate-500 space-y-1">
                    <p class="font-bold text-slate-700 uppercase">Factura generada por sistema Bar Luné POS</p>
                    <!--<p>Resolución DIAN No. 18764000001 de 2026 • Rango Autorizado BM-20260000 a BM-20269999</p>-->
                    <p>Régimen Común • Responsable del Impuesto sobre las Ventas (IVA)</p>
                    <p class="text-slate-400 italic mt-1">¡Gracias por su visita y preferencia!</p>
                </div>
            </div>
        </div>
    </div>
    `;

    // Inyectar el modal al body una vez cargado el DOM
    document.addEventListener('DOMContentLoaded', () => {
        if (!document.getElementById('factura-modal-overlay')) {
            const wrapper = document.createElement('div');
            wrapper.innerHTML = modalHtml;
            document.body.appendChild(wrapper.firstElementChild);

            // Wire up event listeners
            document.getElementById('btn-cerrar-factura').addEventListener('click', closeFacturaModal);
            document.getElementById('factura-modal-overlay').addEventListener('click', (e) => {
                if (e.target.id === 'factura-modal-overlay') closeFacturaModal();
            });
            document.getElementById('btn-imprimir-factura').addEventListener('click', () => {
                window.print();
            });
            document.getElementById('btn-descargar-pdf').addEventListener('click', descargarFacturaPDF);
        }
    });

    let currentFacturaData = null;

    function formatCurrency(val) {
        const num = parseFloat(val) || 0;
        return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0 }).format(num);
    }

    window.openFacturaModal = async function(identifier) {
        if (!identifier) return;
        const modal = document.getElementById('factura-modal-overlay');
        if (!modal) return;

        try {
            // Cargar datos completos de la factura
            const res = await window.api.get(`/api/pagos/${identifier}`);
            if (!res || !res.data) throw new Error("No se pudo cargar la información de la factura");

            const data = res.data;
            currentFacturaData = data;

            // Header emisor
            document.getElementById('factura-emisor-razon').textContent = data.razon_social || 'Bar Luné S.A.S.';
            document.getElementById('factura-emisor-nit').textContent = data.nit || '900.123.456-7';
            document.getElementById('factura-sede-nombre').textContent = data.sede_nombre || 'Sede Principal';
            document.getElementById('factura-sede-dir').textContent = data.sede_direccion || 'Calle Principal';
            document.getElementById('factura-sede-ciudad').textContent = data.sede_ciudad || 'Colombia';
            document.getElementById('factura-sede-tel').textContent = data.sede_telefono || 'N/A';

            // Factura N° & Fechas
            document.getElementById('factura-numero').textContent = data.numero_comprobante || ('BM-' + (data.id || '').slice(0,8).toUpperCase());
            const dt = data.created_at ? new Date(data.created_at) : new Date();
            document.getElementById('factura-fecha').textContent = dt.toISOString().slice(0, 10);
            document.getElementById('factura-hora').textContent = dt.toTimeString().slice(0, 8);

            // Cliente
            document.getElementById('factura-cliente-nombre').textContent = data.cliente_nombre || 'Consumidor Final';
            document.getElementById('factura-cliente-doc').textContent = data.cliente_documento || '222222222222';
            const contacto = [];
            if (data.cliente_telefono) contacto.push('Tel: ' + data.cliente_telefono);
            if (data.cliente_email) contacto.push('Email: ' + data.cliente_email);
            document.getElementById('factura-cliente-contacto').textContent = contacto.join(' • ');

            // Servicio
            document.getElementById('factura-mesa').textContent = 'Mesa ' + (data.mesa || '1');
            document.getElementById('factura-mesero').textContent = data.mesero_nombre || 'N/A';
            document.getElementById('factura-cajero').textContent = data.cajero_nombre || 'Admin Sistema';
            document.getElementById('factura-metodo').textContent = data.metodo_pago || 'EFECTIVO';

            // Items Detalle
            const tbody = document.getElementById('factura-items-tbody');
            tbody.innerHTML = '';

            const items = data.items || [];
            if (items.length > 0) {
                items.forEach(it => {
                    const tr = document.createElement('tr');
                    tr.className = 'hover:bg-slate-50';
                    tr.innerHTML = `
                        <td class="py-2 px-3 text-center font-bold text-slate-800">${it.cantidad}</td>
                        <td class="py-2 px-3">
                            <span class="font-bold text-slate-900">${it.producto_nombre}</span>
                            ${it.producto_codigo ? `<span class="text-[10px] text-slate-400 block font-mono">Cód: ${it.producto_codigo}</span>` : ''}
                        </td>
                        <td class="py-2 px-3 text-right font-mono text-slate-700">${formatCurrency(it.precio_unitario)}</td>
                        <td class="py-2 px-3 text-right font-mono text-slate-600">${formatCurrency(it.impuesto)}</td>
                        <td class="py-2 px-3 text-right font-mono font-bold text-slate-900">${formatCurrency(it.total)}</td>
                    `;
                    tbody.appendChild(tr);
                });
            } else {
                tbody.innerHTML = `
                    <tr>
                        <td class="py-2 px-3 text-center font-bold text-slate-800">1</td>
                        <td class="py-2 px-3 font-bold text-slate-900">Consumo General Mesa ${data.mesa}</td>
                        <td class="py-2 px-3 text-right font-mono text-slate-700">${formatCurrency(data.subtotal)}</td>
                        <td class="py-2 px-3 text-right font-mono text-slate-600">${formatCurrency(data.impuesto)}</td>
                        <td class="py-2 px-3 text-right font-mono font-bold text-slate-900">${formatCurrency(data.total || data.monto_total)}</td>
                    </tr>
                `;
            }

            // Totales
            document.getElementById('factura-subtotal').textContent = formatCurrency(data.subtotal);
            document.getElementById('factura-impuesto').textContent = formatCurrency(data.impuesto);
            
            const propina = parseFloat(data.propina || 0);
            if (propina > 0) {
                document.getElementById('factura-propina-row').style.display = 'flex';
                document.getElementById('factura-propina').textContent = formatCurrency(propina);
            } else {
                document.getElementById('factura-propina-row').style.display = 'none';
            }

            const total = parseFloat(data.monto_total || data.total || 0);
            document.getElementById('factura-total').textContent = formatCurrency(total);

            const rec = parseFloat(data.monto_recibido || 0);
            const cambio = parseFloat(data.cambio || 0);
            if (data.metodo_pago === 'efectivo' && rec > 0) {
                document.getElementById('factura-recibido-row').style.display = 'flex';
                document.getElementById('factura-recibido').textContent = formatCurrency(rec);
                document.getElementById('factura-cambio-row').style.display = 'flex';
                document.getElementById('factura-cambio').textContent = formatCurrency(cambio);
            } else {
                document.getElementById('factura-recibido-row').style.display = 'none';
                document.getElementById('factura-cambio-row').style.display = 'none';
            }

            // Mostrar modal
            modal.style.display = 'flex';
        } catch(e) {
            console.error(e);
            alert("Error al cargar la factura: " + e.message);
        }
    };

    function closeFacturaModal() {
        const modal = document.getElementById('factura-modal-overlay');
        if (modal) modal.style.display = 'none';
    }
    window.closeFacturaModal = closeFacturaModal;

    async function descargarFacturaPDF() {
        const element = document.getElementById('factura-print-area');
        if (!element) return;

        const numComp = currentFacturaData?.numero_comprobante || 'BM-FACTURA';
        const opt = {
            margin:       [10, 10, 10, 10],
            filename:     `Factura_${numComp}.pdf`,
            image:        { type: 'jpeg', quality: 0.98 },
            html2canvas:  { scale: 2, useCORS: true },
            jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
        };

        try {
            if (window.html2pdf) {
                await window.html2pdf().set(opt).from(element).save();
            } else {
                window.print();
            }
        } catch(e) {
            console.error("Error al exportar PDF:", e);
            window.print();
        }
    }
    window.descargarFacturaPDF = descargarFacturaPDF;
})();
