-- ============================================================
-- BAR MUNE — Schema en PUBLIC (para Supabase sin config extra)
-- Ejecutar en Supabase SQL Editor del proyecto Bar_lune
-- ============================================================

-- Extensiones
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- TABLA: sedes
-- ============================================================
CREATE TABLE IF NOT EXISTS public.sedes (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre      VARCHAR(100) NOT NULL,
    direccion   TEXT,
    ciudad      VARCHAR(80),
    telefono    VARCHAR(20),
    capacidad   INTEGER DEFAULT 0,
    estado      VARCHAR(20) DEFAULT 'activa' CHECK (estado IN ('activa', 'inactiva')),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLA: roles
-- ============================================================
CREATE TABLE IF NOT EXISTS public.roles (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre       VARCHAR(50) NOT NULL UNIQUE,
    descripcion  TEXT,
    permisos     JSONB DEFAULT '{}'::JSONB,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO public.roles (nombre, descripcion) VALUES
('admin',  'Administrador con acceso completo'),
('cajero', 'Cajero con acceso a ventas e inventario'),
('mesero', 'Mesero con acceso a órdenes')
ON CONFLICT (nombre) DO NOTHING;

-- ============================================================
-- TABLA: usuarios
-- ============================================================
CREATE TABLE IF NOT EXISTS public.usuarios (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email          VARCHAR(150) NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    nombre         VARCHAR(100) NOT NULL,
    apellido       VARCHAR(100) NOT NULL DEFAULT '',
    telefono       VARCHAR(20),
    rol_id         UUID NOT NULL REFERENCES public.roles(id),
    sede_id        UUID REFERENCES public.sedes(id),
    estado         VARCHAR(20) DEFAULT 'activo' CHECK (estado IN ('activo', 'inactivo')),
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLA: categorias
-- ============================================================
CREATE TABLE IF NOT EXISTS public.categorias (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre       VARCHAR(80) NOT NULL,
    descripcion  TEXT,
    color        VARCHAR(7) DEFAULT '#6366F1',
    activa       BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO public.categorias (nombre, descripcion, color) VALUES
('Cervezas',    'Cervezas nacionales e importadas', '#F59E0B'),
('Licores',     'Whisky, ron, vodka, gin y más',    '#8B5CF6'),
('Cocteles',    'Bebidas preparadas y cocteles',     '#EC4899'),
('Sin Alcohol', 'Jugos, gaseosas y agua',            '#10B981'),
('Snacks',      'Comida y aperitivos',               '#F97316'),
('Vinos',       'Vinos tintos, blancos y rosados',   '#EF4444')
ON CONFLICT DO NOTHING;

-- ============================================================
-- TABLA: productos
-- ============================================================
CREATE TABLE IF NOT EXISTS public.productos (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    codigo         VARCHAR(50) NOT NULL,
    nombre         VARCHAR(150) NOT NULL,
    descripcion    TEXT,
    precio_costo   NUMERIC(12, 2) NOT NULL DEFAULT 0,
    precio_venta   NUMERIC(12, 2) NOT NULL DEFAULT 0,
    stock_actual   INTEGER NOT NULL DEFAULT 0,
    stock_minimo   INTEGER NOT NULL DEFAULT 5,
    categoria_id   UUID REFERENCES public.categorias(id),
    sede_id        UUID REFERENCES public.sedes(id),
    estado         VARCHAR(20) DEFAULT 'activo' CHECK (estado IN ('activo', 'inactivo', 'agotado')),
    imagen_url     TEXT,
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (codigo, sede_id)
);

-- ============================================================
-- TABLA: ordenes
-- ============================================================
CREATE SEQUENCE IF NOT EXISTS public.ordenes_numero_seq START 1000;

CREATE TABLE IF NOT EXISTS public.ordenes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    numero_orden    INTEGER UNIQUE DEFAULT nextval('public.ordenes_numero_seq'),
    mesa            VARCHAR(20) NOT NULL,
    sede_id         UUID NOT NULL REFERENCES public.sedes(id),
    mesero_id       UUID REFERENCES public.usuarios(id),
    estado          VARCHAR(20) DEFAULT 'abierta' CHECK (estado IN ('abierta', 'en_proceso', 'lista', 'pagada', 'cancelada')),
    subtotal        NUMERIC(12, 2) DEFAULT 0,
    impuesto        NUMERIC(12, 2) DEFAULT 0,
    total           NUMERIC(12, 2) DEFAULT 0,
    notas           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLA: orden_items
-- ============================================================
CREATE TABLE IF NOT EXISTS public.orden_items (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    orden_id         UUID NOT NULL REFERENCES public.ordenes(id) ON DELETE CASCADE,
    producto_id      UUID NOT NULL REFERENCES public.productos(id),
    cantidad         INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario  NUMERIC(12, 2) NOT NULL,
    subtotal         NUMERIC(12, 2) NOT NULL DEFAULT 0,
    notas            TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLA: pagos
-- ============================================================
CREATE TABLE IF NOT EXISTS public.pagos (
    id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    orden_id           UUID NOT NULL UNIQUE REFERENCES public.ordenes(id),
    cajero_id          UUID REFERENCES public.usuarios(id),
    metodo_pago        VARCHAR(20) NOT NULL CHECK (metodo_pago IN ('efectivo', 'tarjeta', 'transferencia')),
    monto_total        NUMERIC(12, 2) NOT NULL,
    monto_recibido     NUMERIC(12, 2) DEFAULT 0,
    cambio             NUMERIC(12, 2) DEFAULT 0,
    propina            NUMERIC(12, 2) DEFAULT 0,
    numero_comprobante VARCHAR(30) UNIQUE,
    created_at         TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLA: parametros_sistema
-- ============================================================
CREATE TABLE IF NOT EXISTS public.parametros_sistema (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clave        VARCHAR(80) NOT NULL UNIQUE,
    valor        TEXT NOT NULL,
    descripcion  TEXT,
    tipo         VARCHAR(20) DEFAULT 'string',
    categoria    VARCHAR(50) DEFAULT 'general',
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO public.parametros_sistema (clave, valor, descripcion, tipo, categoria) VALUES
('impuesto_porcentaje', '19',        'Porcentaje de IVA aplicado a las ventas', 'number',  'impuestos'),
('moneda',             'COP',        'Moneda del sistema',                       'string',  'general'),
('nombre_negocio',     'Bar Mune',   'Nombre del negocio',                       'string',  'general'),
('mesas_por_sede',     '20',         'Número máximo de mesas por sede',          'number',  'operacion'),
('stock_alerta_activa','true',       'Activar alertas de stock bajo',             'boolean', 'inventario'),
('dias_reporte_default','30',        'Días por defecto para reportes',            'number',  'reportes')
ON CONFLICT (clave) DO NOTHING;

-- ============================================================
-- TABLA: movimientos_inventario
-- ============================================================
CREATE TABLE IF NOT EXISTS public.movimientos_inventario (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    producto_id     UUID NOT NULL REFERENCES public.productos(id),
    tipo            VARCHAR(20) NOT NULL CHECK (tipo IN ('entrada', 'salida', 'ajuste')),
    cantidad        INTEGER NOT NULL,
    stock_anterior  INTEGER NOT NULL,
    stock_nuevo     INTEGER NOT NULL,
    referencia      TEXT,
    usuario_id      UUID REFERENCES public.usuarios(id),
    notas           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TRIGGERS: updated_at automático
-- ============================================================
CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sedes_updated_at ON public.sedes;
CREATE TRIGGER trg_sedes_updated_at BEFORE UPDATE ON public.sedes FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

DROP TRIGGER IF EXISTS trg_usuarios_updated_at ON public.usuarios;
CREATE TRIGGER trg_usuarios_updated_at BEFORE UPDATE ON public.usuarios FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

DROP TRIGGER IF EXISTS trg_productos_updated_at ON public.productos;
CREATE TRIGGER trg_productos_updated_at BEFORE UPDATE ON public.productos FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

DROP TRIGGER IF EXISTS trg_ordenes_updated_at ON public.ordenes;
CREATE TRIGGER trg_ordenes_updated_at BEFORE UPDATE ON public.ordenes FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- ============================================================
-- USUARIO ADMIN INICIAL
-- Sede por defecto
-- ============================================================
INSERT INTO public.sedes (id, nombre, direccion, ciudad, capacidad)
VALUES ('11111111-1111-1111-1111-111111111111', 'Sede Principal', 'Calle 123 #45-67', 'Bogotá', 80)
ON CONFLICT (id) DO NOTHING;

-- Admin: admin@barmune.com / Admin123!
INSERT INTO public.usuarios (email, password_hash, nombre, apellido, rol_id, sede_id, estado)
SELECT
    'admin@barmune.com',
    '$2b$12$S5WFKLLaeIGLJLWnmYNqkOMFzjL7ZLpWsoiYMc3yRDdUL6TiMtjau',
    'Admin',
    'Sistema',
    r.id,
    '11111111-1111-1111-1111-111111111111',
    'activo'
FROM public.roles r WHERE r.nombre = 'admin'
ON CONFLICT (email) DO NOTHING;

-- Verificar
SELECT 'sedes' as tabla, count(*) FROM public.sedes
UNION ALL SELECT 'roles', count(*) FROM public.roles
UNION ALL SELECT 'usuarios', count(*) FROM public.usuarios
UNION ALL SELECT 'categorias', count(*) FROM public.categorias
UNION ALL SELECT 'parametros', count(*) FROM public.parametros_sistema;
