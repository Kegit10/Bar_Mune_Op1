-- ============================================================
-- CORRECCION: Actualizar hash del usuario admin
-- Ejecutar en Supabase SQL Editor
-- Password: Admin123!
-- ============================================================

-- Opción A: Si ya ejecutaste schema.sql — solo actualizar el hash
UPDATE bar_mune.usuarios
SET password_hash = '$2b$12$S5WFKLLaeIGLJLWnmYNqkOMFzjL7ZLpWsoiYMc3yRDdUL6TiMtjau'
WHERE email = 'admin@barmune.com';

-- Verificar que se actualizó
SELECT id, email, nombre, estado FROM bar_mune.usuarios WHERE email = 'admin@barmune.com';


-- ============================================================
-- Opción B: Si NO ejecutaste schema.sql aún — usar este INSERT completo
-- (reemplaza el INSERT del schema.sql)
-- ============================================================
/*
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
*/
