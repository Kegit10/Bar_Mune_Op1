import uuid
import datetime
from decimal import Decimal
from flask import Blueprint, request, jsonify
from app.db import query, query_one, execute, execute_one
from app.utils.decorators import require_auth, require_roles
import bcrypt

usuarios_bp = Blueprint('usuarios', __name__, url_prefix='/api/usuarios')


def serialize(row):
    if row is None:
        return None
    if isinstance(row, list):
        return [serialize(r) for r in row]
    if isinstance(row, dict):
        result = {}
        for k, v in row.items():
            if isinstance(v, uuid.UUID):
                result[k] = str(v)
            elif isinstance(v, Decimal):
                result[k] = float(v)
            elif isinstance(v, (datetime.datetime, datetime.date, datetime.time)):
                result[k] = v.isoformat()
            else:
                result[k] = v
        return result
    return row


def resolve_rol_id(rol_val):
    """Resuelve un rol_id ya sea pasado como UUID o como nombre ('admin', 'cajero', 'mesero')."""
    if not rol_val:
        return None
    rol_str = str(rol_val).strip()
    # Si es nombre de rol
    rol = query_one("SELECT id FROM public.roles WHERE LOWER(nombre) = %s OR id::text = %s", (rol_str.lower(), rol_str))
    if rol:
        return str(rol['id'])
    return None


@usuarios_bp.route('/roles', methods=['GET'])
@require_auth
def get_roles():
    """Obtiene la lista de roles del sistema."""
    try:
        roles = query("SELECT id, nombre, descripcion FROM public.roles ORDER BY nombre ASC", ())
        return jsonify({"success": True, "message": "Roles obtenidos", "data": serialize(roles)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@usuarios_bp.route('', methods=['GET'])
@require_auth
def get_usuarios():
    try:
        sede_id = request.args.get('sede_id')
        rol_id = request.args.get('rol_id')
        search = request.args.get('search')
        limit = request.args.get('limit', 100)

        sql = """
            SELECT u.id, u.email, u.nombre, u.apellido, u.telefono, u.estado, u.created_at, u.rol_id, u.sede_id,
                   r.nombre as rol_nombre, s.nombre as sede_nombre
            FROM public.usuarios u
            LEFT JOIN public.roles r ON u.rol_id = r.id
            LEFT JOIN public.sedes s ON u.sede_id = s.id
            WHERE 1=1
        """
        params = []

        if sede_id:
            sql += " AND u.sede_id = %s"
            params.append(sede_id)
        if rol_id:
            # Puede ser UUID o nombre de rol
            resolved_rol = resolve_rol_id(rol_id)
            if resolved_rol:
                sql += " AND u.rol_id = %s"
                params.append(resolved_rol)
            else:
                sql += " AND LOWER(r.nombre) = %s"
                params.append(rol_id.lower())
        if search:
            sql += " AND (u.nombre ILIKE %s OR u.apellido ILIKE %s OR u.email ILIKE %s)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

        sql += " ORDER BY u.created_at DESC LIMIT %s"
        params.append(int(limit))

        rows = query(sql, tuple(params))
        # Formatear campo rol para compatibilidad con frontend
        serialized = serialize(rows)
        for u in serialized:
            u['rol'] = u.get('rol_nombre', '')
        return jsonify({"success": True, "message": "Usuarios obtenidos", "data": serialized}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@usuarios_bp.route('/<id>', methods=['GET'])
@require_auth
def get_usuario(id):
    try:
        sql = """
            SELECT u.id, u.email, u.nombre, u.apellido, u.telefono, u.estado, u.created_at, u.rol_id, u.sede_id,
                   r.nombre as rol_nombre, s.nombre as sede_nombre
            FROM public.usuarios u
            LEFT JOIN public.roles r ON u.rol_id = r.id
            LEFT JOIN public.sedes s ON u.sede_id = s.id
            WHERE u.id = %s
        """
        row = query_one(sql, (id,))
        if not row:
            return jsonify({"success": False, "message": "Usuario no encontrado", "data": None}), 404
        serialized = serialize(row)
        serialized['rol'] = serialized.get('rol_nombre', '')
        return jsonify({"success": True, "message": "Usuario obtenido", "data": serialized}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@usuarios_bp.route('', methods=['POST'])
@require_auth
@require_roles('admin')
def create_usuario():
    try:
        data = request.get_json() or {}
        email = (data.get('email') or '').strip().lower()
        password = data.get('password')
        nombre = (data.get('nombre') or '').strip()
        apellido = (data.get('apellido') or '').strip()
        rol_input = data.get('rol_id') or data.get('rol')
        sede_id = data.get('sede_id') or None
        estado = data.get('estado', 'activo')
        telefono = data.get('telefono', '')

        if not email or not password or not nombre:
            return jsonify({"success": False, "message": "Email, contraseña y nombre son requeridos", "data": None}), 400

        rol_id = resolve_rol_id(rol_input)
        if not rol_id:
            return jsonify({"success": False, "message": f"Rol inválido: '{rol_input}'", "data": None}), 400

        # Verificar unicidad de email
        existing = query_one("SELECT id FROM public.usuarios WHERE LOWER(email) = %s", (email,))
        if existing:
            return jsonify({"success": False, "message": "El correo electrónico ya se encuentra registrado", "data": None}), 400

        # Generar hash bcrypt
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')

        sql = """
            INSERT INTO public.usuarios (email, password_hash, nombre, apellido, telefono, rol_id, sede_id, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, email, nombre, apellido, telefono, rol_id, sede_id, estado, created_at
        """
        row = execute_one(sql, (email, hashed_pw, nombre, apellido, telefono, rol_id, sede_id, estado))

        # Consultar con joins
        user_created = query_one(
            """SELECT u.id, u.email, u.nombre, u.apellido, u.telefono, u.estado, u.created_at, u.rol_id, u.sede_id,
                      r.nombre as rol_nombre, s.nombre as sede_nombre
               FROM public.usuarios u
               LEFT JOIN public.roles r ON u.rol_id = r.id
               LEFT JOIN public.sedes s ON u.sede_id = s.id
               WHERE u.id = %s""",
            (row['id'],)
        )
        serialized = serialize(user_created)
        serialized['rol'] = serialized.get('rol_nombre', '')
        return jsonify({"success": True, "message": "Usuario creado exitosamente", "data": serialized}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@usuarios_bp.route('/<id>', methods=['PUT'])
@require_auth
@require_roles('admin')
def update_usuario(id):
    try:
        data = request.get_json() or {}
        user = query_one("SELECT id FROM public.usuarios WHERE id = %s", (id,))
        if not user:
            return jsonify({"success": False, "message": "Usuario no encontrado", "data": None}), 404

        updates = []
        params = []

        if 'nombre' in data:
            updates.append("nombre = %s")
            params.append(data['nombre'].strip())
        if 'apellido' in data:
            updates.append("apellido = %s")
            params.append(data['apellido'].strip())
        if 'telefono' in data:
            updates.append("telefono = %s")
            params.append(data['telefono'].strip())
        if 'email' in data:
            new_email = data['email'].strip().lower()
            existing = query_one("SELECT id FROM public.usuarios WHERE LOWER(email) = %s AND id != %s", (new_email, id))
            if existing:
                return jsonify({"success": False, "message": "El email ya está en uso por otro usuario", "data": None}), 400
            updates.append("email = %s")
            params.append(new_email)
        if 'rol_id' in data or 'rol' in data:
            rol_val = data.get('rol_id') or data.get('rol')
            resolved_rol = resolve_rol_id(rol_val)
            if resolved_rol:
                updates.append("rol_id = %s")
                params.append(resolved_rol)
        if 'sede_id' in data:
            updates.append("sede_id = %s")
            params.append(data['sede_id'] if data['sede_id'] else None)
        if 'estado' in data:
            updates.append("estado = %s")
            params.append(data['estado'])
        if data.get('password'):
            hashed_pw = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')
            updates.append("password_hash = %s")
            params.append(hashed_pw)

        if not updates:
            return jsonify({"success": False, "message": "No se enviaron campos para actualizar", "data": None}), 400

        updates.append("updated_at = NOW()")
        sql = f"UPDATE public.usuarios SET {', '.join(updates)} WHERE id = %s RETURNING id"
        params.append(id)
        execute_one(sql, tuple(params))

        user_updated = query_one(
            """SELECT u.id, u.email, u.nombre, u.apellido, u.telefono, u.estado, u.created_at, u.rol_id, u.sede_id,
                      r.nombre as rol_nombre, s.nombre as sede_nombre
               FROM public.usuarios u
               LEFT JOIN public.roles r ON u.rol_id = r.id
               LEFT JOIN public.sedes s ON u.sede_id = s.id
               WHERE u.id = %s""",
            (id,)
        )
        serialized = serialize(user_updated)
        serialized['rol'] = serialized.get('rol_nombre', '')
        return jsonify({"success": True, "message": "Usuario actualizado exitosamente", "data": serialized}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@usuarios_bp.route('/<id>', methods=['DELETE'])
@require_auth
@require_roles('admin')
def delete_usuario(id):
    try:
        user = query_one("SELECT id FROM public.usuarios WHERE id = %s", (id,))
        if not user:
            return jsonify({"success": False, "message": "Usuario no encontrado", "data": None}), 404

        sql = "UPDATE public.usuarios SET estado = 'inactivo', updated_at = NOW() WHERE id = %s RETURNING id"
        row = execute_one(sql, (id,))
        return jsonify({"success": True, "message": "Usuario desactivado exitosamente", "data": serialize(row)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500
