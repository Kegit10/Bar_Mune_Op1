-- ============================================================
-- BAR MUNE — Schema de Base de Datos
-- Ejecutar en Supabase SQL Editor
-- Schema: bar_mune
-- ============================================================

-- Crear schema dedicado
CREATE SCHEMA IF NOT EXISTS bar_mune;

-- Extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- TABLA: sedes
-- ============================================================
CREATE TABLE bar_mune.sedes (
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
CREATE TABLE bar_mune.roles (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre       VARCHAR(50) NOT NULL UNIQUE CHECK (nombre IN ('admin', 'cajero', 'mesero')),
    descripcion  TEXT,
    permisos     JSONB DEFAULT '{}'::JSONB,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Roles iniciales
INSERT INTO bar_mune.roles (nombre, descripcion, permisos) VALUES
('admin', 'Administrador con acceso completo', '{"usuarios":["read","write","delete"],"sedes":["read","write","delete"],"inventario":["read","write","delete"],"ordenes":["read","write","delete"],"pagos":["read","write"],"reportes":["read"],"parametros":["read","write"]}'::JSONB),
('cajero', 'Cajero con acceso a ventas e inventario', '{"inventario":["read","write"],"ordenes":["read","write"],"pagos":["read","write"],"reportes":["read"]}'::JSONB),
('mesero', 'Mesero con acceso a órdenes', '{"ordenes":["read","write"]}'::JSONB);

-- ============================================================
-- TABLA: usuarios
-- ============================================================
CREATE TABLE bar_mune.usuarios (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email          VARCHAR(150) NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    nombre         VARCHAR(100) NOT NULL,
    apellido       VARCHAR(100) NOT NULL,
    telefono       VARCHAR(20),
    rol_id         UUID NOT NULL REFERENCES bar_mune.roles(id),
    sede_id        UUID REFERENCES bar_mune.sedes(id),
    estado         VARCHAR(20) DEFAULT 'activo' CHECK (estado IN ('activo', 'inactivo')),
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_usuarios_email ON bar_mune.usuarios(email);
CREATE INDEX idx_usuarios_sede ON bar_mune.usuarios(sede_id);
CREATE INDEX idx_usuarios_rol ON bar_mune.usuarios(rol_id);

-- ============================================================
-- TABLA: categorias
-- ============================================================
CREATE TABLE bar_mune.categorias (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre       VARCHAR(80) NOT NULL,
    descripcion  TEXT,
    color        VARCHAR(7) DEFAULT '#6366F1',
    activa       BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Categorías iniciales
INSERT INTO bar_mune.categorias (nombre, descripcion, color) VALUES
('Cervezas', 'Cervezas nacionales e importadas', '#F59E0B'),
('Licores', 'Whisky, ron, vodka, gin y más', '#8B5CF6'),
('Cocteles', 'Bebidas preparadas y cocteles', '#EC4899'),
('Sin Alcohol', 'Jugos, gaseosas y agua', '#10B981'),
('Snacks', 'Comida y aperitivos', '#F97316'),
('Vinos', 'Vinos tintos, blancos y rosados', '#EF4444');

-- ============================================================
-- TABLA: productos
-- ============================================================
CREATE TABLE bar_mune.productos (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    codigo         VARCHAR(50) NOT NULL,
    nombre         VARCHAR(150) NOT NULL,
    descripcion    TEXT,
    precio_costo   NUMERIC(12, 2) NOT NULL DEFAULT 0,
    precio_venta   NUMERIC(12, 2) NOT NULL DEFAULT 0,
    stock_actual   INTEGER NOT NULL DEFAULT 0,
    stock_minimo   INTEGER NOT NULL DEFAULT 5,
    categoria_id   UUID REFERENCES bar_mune.categorias(id),
    sede_id        UUID REFERENCES bar_mune.sedes(id),
    estado         VARCHAR(20) DEFAULT 'activo' CHECK (estado IN ('activo', 'inactivo', 'agotado')),
    imagen_url     TEXT,
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (codigo, sede_id)
);

CREATE INDEX idx_productos_sede ON bar_mune.productos(sede_id);
CREATE INDEX idx_productos_categoria ON bar_mune.productos(categoria_id);
CREATE INDEX idx_productos_estado ON bar_mune.productos(estado);
CREATE INDEX idx_productos_stock ON bar_mune.productos(stock_actual, stock_minimo);

-- ============================================================
-- TABLA: ordenes
-- ============================================================
CREATE SEQUENCE IF NOT EXISTS bar_mune.ordenes_numero_seq START 1000;

CREATE TABLE bar_mune.ordenes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    numero_orden    INTEGER UNIQUE DEFAULT nextval('bar_mune.ordenes_numero_seq'),
    mesa            VARCHAR(20) NOT NULL,
    sede_id         UUID NOT NULL REFERENCES bar_mune.sedes(id),
    mesero_id       UUID REFERENCES bar_mune.usuarios(id),
    estado          VARCHAR(20) DEFAULT 'abierta' CHECK (estado IN ('abierta', 'en_proceso', 'lista', 'pagada', 'cancelada')),
    subtotal        NUMERIC(12, 2) DEFAULT 0,
    impuesto        NUMERIC(12, 2) DEFAULT 0,
    total           NUMERIC(12, 2) DEFAULT 0,
    notas           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ordenes_sede ON bar_mune.ordenes(sede_id);
CREATE INDEX idx_ordenes_estado ON bar_mune.ordenes(estado);
CREATE INDEX idx_ordenes_mesero ON bar_mune.ordenes(mesero_id);
CREATE INDEX idx_ordenes_fecha ON bar_mune.ordenes(created_at);

-- ============================================================
-- TABLA: orden_items
-- ============================================================
CREATE TABLE bar_mune.orden_items (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    orden_id         UUID NOT NULL REFERENCES bar_mune.ordenes(id) ON DELETE CASCADE,
    producto_id      UUID NOT NULL REFERENCES bar_mune.productos(id),
    cantidad         INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario  NUMERIC(12, 2) NOT NULL,
    subtotal         NUMERIC(12, 2) GENERATED ALWAYS AS (cantidad * precio_unitario) STORED,
    notas            TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_orden_items_orden ON bar_mune.orden_items(orden_id);

-- ============================================================
-- TABLA: pagos
-- ============================================================
CREATE TABLE bar_mune.pagos (
    id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    orden_id           UUID NOT NULL UNIQUE REFERENCES bar_mune.ordenes(id),
    cajero_id          UUID REFERENCES bar_mune.usuarios(id),
    metodo_pago        VARCHAR(20) NOT NULL CHECK (metodo_pago IN ('efectivo', 'tarjeta', 'transferencia')),
    monto_total        NUMERIC(12, 2) NOT NULL,
    monto_recibido     NUMERIC(12, 2) DEFAULT 0,
    cambio             NUMERIC(12, 2) DEFAULT 0,
    propina            NUMERIC(12, 2) DEFAULT 0,
    numero_comprobante VARCHAR(20) UNIQUE,
    created_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pagos_orden ON bar_mune.pagos(orden_id);
CREATE INDEX idx_pagos_fecha ON bar_mune.pagos(created_at);

-- Función para generar número de comprobante
CREATE OR REPLACE FUNCTION bar_mune.generar_comprobante()
RETURNS TRIGGER AS $$
BEGIN
    NEW.numero_comprobante := 'BM-' || TO_CHAR(NOW(), 'YYYYMMDD') || '-' || LPAD(CAST(FLOOR(RANDOM() * 99999) AS TEXT), 5, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_comprobante
BEFORE INSERT ON bar_mune.pagos
FOR EACH ROW
WHEN (NEW.numero_comprobante IS NULL)
EXECUTE FUNCTION bar_mune.generar_comprobante();

-- ============================================================
-- TABLA: parametros_sistema
-- ============================================================
CREATE TABLE bar_mune.parametros_sistema (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clave        VARCHAR(80) NOT NULL UNIQUE,
    valor        TEXT NOT NULL,
    descripcion  TEXT,
    tipo         VARCHAR(20) DEFAULT 'string' CHECK (tipo IN ('string', 'number', 'boolean', 'json')),
    categoria    VARCHAR(50) DEFAULT 'general',
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Parámetros iniciales
INSERT INTO bar_mune.parametros_sistema (clave, valor, descripcion, tipo, categoria) VALUES
('impuesto_porcentaje', '19', 'Porcentaje de impuesto (IVA) aplicado a las ventas', 'number', 'impuestos'),
('moneda', 'COP', 'Moneda del sistema', 'string', 'general'),
('nombre_negocio', 'Bar Mune', 'Nombre del negocio', 'string', 'general'),
('mesas_por_sede', '20', 'Número máximo de mesas por sede', 'number', 'operacion'),
('stock_alerta_activa', 'true', 'Activar alertas de stock bajo', 'boolean', 'inventario'),
('dias_reporte_default', '30', 'Días por defecto para reportes', 'number', 'reportes'),
('logo_url', '', 'URL del logo del negocio', 'string', 'general'),
('horario_apertura', '12:00', 'Hora de apertura', 'string', 'operacion'),
('horario_cierre', '03:00', 'Hora de cierre', 'string', 'operacion');

-- ============================================================
-- TABLA: movimientos_inventario
-- ============================================================
CREATE TABLE bar_mune.movimientos_inventario (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    producto_id     UUID NOT NULL REFERENCES bar_mune.productos(id),
    tipo            VARCHAR(20) NOT NULL CHECK (tipo IN ('entrada', 'salida', 'ajuste')),
    cantidad        INTEGER NOT NULL,
    stock_anterior  INTEGER NOT NULL,
    stock_nuevo     INTEGER NOT NULL,
    referencia      TEXT,
    usuario_id      UUID REFERENCES bar_mune.usuarios(id),
    notas           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_mov_inv_producto ON bar_mune.movimientos_inventario(producto_id);
CREATE INDEX idx_mov_inv_fecha ON bar_mune.movimientos_inventario(created_at);

-- ============================================================
-- TRIGGERS: updated_at automático
-- ============================================================
CREATE OR REPLACE FUNCTION bar_mune.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sedes_updated_at BEFORE UPDATE ON bar_mune.sedes FOR EACH ROW EXECUTE FUNCTION bar_mune.update_updated_at();
CREATE TRIGGER trg_usuarios_updated_at BEFORE UPDATE ON bar_mune.usuarios FOR EACH ROW EXECUTE FUNCTION bar_mune.update_updated_at();
CREATE TRIGGER trg_productos_updated_at BEFORE UPDATE ON bar_mune.productos FOR EACH ROW EXECUTE FUNCTION bar_mune.update_updated_at();
CREATE TRIGGER trg_ordenes_updated_at BEFORE UPDATE ON bar_mune.ordenes FOR EACH ROW EXECUTE FUNCTION bar_mune.update_updated_at();
CREATE TRIGGER trg_parametros_updated_at BEFORE UPDATE ON bar_mune.parametros_sistema FOR EACH ROW EXECUTE FUNCTION bar_mune.update_updated_at();

-- ============================================================
-- TRIGGER: Actualizar totales de orden al agregar/quitar items
-- ============================================================
CREATE OR REPLACE FUNCTION bar_mune.recalcular_orden_total()
RETURNS TRIGGER AS $$
DECLARE
    v_subtotal NUMERIC;
    v_impuesto_pct NUMERIC;
    v_impuesto NUMERIC;
    v_orden_id UUID;
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_orden_id := OLD.orden_id;
    ELSE
        v_orden_id := NEW.orden_id;
    END IF;

    SELECT COALESCE(SUM(subtotal), 0) INTO v_subtotal
    FROM bar_mune.orden_items
    WHERE orden_id = v_orden_id;

    SELECT CAST(valor AS NUMERIC) INTO v_impuesto_pct
    FROM bar_mune.parametros_sistema
    WHERE clave = 'impuesto_porcentaje';

    v_impuesto := ROUND(v_subtotal * (COALESCE(v_impuesto_pct, 19) / 100), 2);

    UPDATE bar_mune.ordenes
    SET subtotal = v_subtotal,
        impuesto = v_impuesto,
        total = v_subtotal + v_impuesto,
        updated_at = NOW()
    WHERE id = v_orden_id;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_recalcular_total
AFTER INSERT OR UPDATE OR DELETE ON bar_mune.orden_items
FOR EACH ROW EXECUTE FUNCTION bar_mune.recalcular_orden_total();

-- ============================================================
-- ROW LEVEL SECURITY (RLS)
-- Deshabilitado por ahora — la API Flask controla accesos
-- Activar si se usa Supabase Auth directamente
-- ============================================================
ALTER TABLE bar_mune.sedes DISABLE ROW LEVEL SECURITY;
ALTER TABLE bar_mune.roles DISABLE ROW LEVEL SECURITY;
ALTER TABLE bar_mune.usuarios DISABLE ROW LEVEL SECURITY;
ALTER TABLE bar_mune.categorias DISABLE ROW LEVEL SECURITY;
ALTER TABLE bar_mune.productos DISABLE ROW LEVEL SECURITY;
ALTER TABLE bar_mune.ordenes DISABLE ROW LEVEL SECURITY;
ALTER TABLE bar_mune.orden_items DISABLE ROW LEVEL SECURITY;
ALTER TABLE bar_mune.pagos DISABLE ROW LEVEL SECURITY;
ALTER TABLE bar_mune.parametros_sistema DISABLE ROW LEVEL SECURITY;
ALTER TABLE bar_mune.movimientos_inventario DISABLE ROW LEVEL SECURITY;

-- ============================================================
-- GRANT: acceso al rol anon y service_role
-- ============================================================
GRANT USAGE ON SCHEMA bar_mune TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA bar_mune TO service_role;
GRANT SELECT ON ALL TABLES IN SCHEMA bar_mune TO anon, authenticated;
GRANT USAGE ON SEQUENCE bar_mune.ordenes_numero_seq TO service_role;

-- ============================================================
-- DATOS DE PRUEBA (seed)
-- ============================================================

-- Sede principal
INSERT INTO bar_mune.sedes (id, nombre, direccion, ciudad, telefono, capacidad) VALUES
('11111111-1111-1111-1111-111111111111', 'Sede Principal', 'Calle 123 #45-67', 'Bogotá', '601-234-5678', 80);

-- Usuario admin por defecto (password: Admin123!)
-- Hash generado con bcrypt (cost 12)
INSERT INTO bar_mune.usuarios (email, password_hash, nombre, apellido, rol_id, sede_id, estado)
SELECT 
    'admin@barmune.com',
    '$2b$12$S5WFKLLaeIGLJLWnmYNqkOMFzjL7ZLpWsoiYMc3yRDdUL6TiMtjau',
    'Admin',
    'Sistema',
    r.id,
    '11111111-1111-1111-1111-111111111111',
    'activo'
FROM bar_mune.roles r WHERE r.nombre = 'admin';
