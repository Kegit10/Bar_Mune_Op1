# Bar Mune 🍺 — Sistema de Gestión de Bar

Sistema de gestión integral para bares con backend Flask (Python) y frontend HTML/CSS/JS, respaldado por Supabase.

## 📁 Estructura

```
Bar_Mune/
├── backend/          # API REST Flask
├── frontend/         # Interfaz de usuario
└── database/         # Scripts SQL
```

## 🗄️ 1. Configurar Base de Datos (Supabase)

1. Ir a [supabase.com](https://supabase.com) → tu proyecto
2. Abrir **SQL Editor**
3. Ejecutar el archivo `database/schema.sql`

**Credenciales iniciales:**
- Email: `admin@barmune.com`
- Password: `Admin123!`

> ⚠️ **Cambia la contraseña del admin después del primer login**

## ⚙️ 2. Configurar Backend

```bash
cd backend

# 1. Crear entorno virtual
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
# Editar .env y agregar las claves de Supabase

# 4. Ejecutar servidor
python run.py
```

El backend corre en `http://localhost:5000`

### Variables de entorno (.env)

| Variable | Descripción |
|----------|-------------|
| `SUPABASE_URL` | URL del proyecto Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Clave de servicio (Settings → API) |
| `JWT_SECRET_KEY` | Clave secreta para JWT (cualquier string seguro) |

## 🎨 3. Ejecutar Frontend

El frontend es HTML/CSS/JS puro — no requiere build tools.

**Opción A: Live Server (VS Code)**
- Instalar extensión "Live Server"
- Abrir `frontend/index.html` → clic derecho → "Open with Live Server"

**Opción B: Python HTTP Server**
```bash
cd frontend
python -m http.server 8080
# Abrir http://localhost:8080
```

## 🔑 Roles y Permisos

| Rol | Acceso |
|-----|--------|
| **Admin** | Todo: usuarios, sedes, inventario, órdenes, pagos, reportes, parámetros |
| **Cajero** | Inventario, órdenes, pagos, reportes |
| **Mesero** | Solo órdenes (crear, agregar productos) |

## 📋 API Endpoints

| Módulo | Base URL |
|--------|----------|
| Auth | `POST /api/auth/login` |
| Usuarios | `GET/POST /api/usuarios` |
| Sedes | `GET/POST /api/sedes` |
| Parámetros | `GET/PUT /api/parametros` |
| Productos | `GET/POST /api/productos` |
| Alertas Stock | `GET /api/productos/alertas` |
| Órdenes | `GET/POST /api/ordenes` |
| Items | `POST /api/ordenes/:id/items` |
| Pagos | `GET/POST /api/pagos` |
| Reportes | `GET /api/reportes/ventas` |

## 🚀 Historias de Usuario Implementadas

- **HU-01** Modificación de Usuarios ✅
- **HU-02** Visualización de Usuarios ✅
- **HU-03** Creación de Sedes ✅
- **HU-04** Parametrización del Sistema ✅
- **HU-05** Edición de Productos en Inventario ✅
- **HU-06** Generación de Reporte de Inventario (XLS/CSV) ✅
- **HU-07** Control de Stock y Alertas ✅
- **HU-08** Registro de Productos ✅
- **HU-09** Crear una Orden ✅
- **HU-10** Registrar un Pago ✅
- **HU-11** Generar Reporte de Ventas ✅
- **HU-12** Agregar Productos a una Orden ✅
