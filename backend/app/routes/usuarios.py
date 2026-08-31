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

@usuarios_bp.route('', methods=['GET'])
@require_auth
def get_usuarios():
    try:
        sede_id = request.args.get('sede_id')
        rol_id = request.args.get('rol_id')
        search = request.args.get('search')
        limit = request.args.get('limit', 100)
        
        sql = """
            SELECT u.id, u.email, u.nombres, u.apellidos, u.estado, u.creado_en, u.rol_id, u.sede_id,
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
            sql += " AND u.rol_id = %s"
            params.append(rol_id)
        if search:
            sql += " AND (u.nombres ILIKE %s OR u.apellidos ILIKE %s OR u.email ILIKE %s)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
            
        sql += " ORDER BY u.creado_en DESC LIMIT %s"
        params.append(int(limit))
        
        rows = query(sql, tuple(params))
        return jsonify({"success": True, "message": "Usuarios obtenidos", "data": serialize(rows)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@usuarios_bp.route('/<id>', methods=['GET'])
@require_auth
def get_usuario(id):
    try:
        sql = """
            SELECT u.id, u.email, u.nombres, u.apellidos, u.estado, u.creado_en, u.rol_id, u.sede_id,
                   r.nombre as rol_nombre, s.nombre as sede_nombre
            FROM public.usuarios u
            LEFT JOIN public.roles r ON u.rol_id = r.id
            LEFT JOIN public.sedes s ON u.sede_id = s.id
            WHERE u.id = %s
        """
        row = query_one(sql, (id,))
        if not row:
            return jsonify({"success": False, "message": "Usuario no encontrado", "data": None}), 404
        return jsonify({"success": True, "message": "Usuario obtenido", "data": serialize(row)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@usuarios_bp.route('', methods=['POST'])
@require_auth
@require_roles(['admin'])
def create_usuario():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        nombres = data.get('nombres')
        apellidos = data.get('apellidos')
        rol_id = data.get('rol_id')
        sede_id = data.get('sede_id')
        estado = data.get('estado', 'activo')
        
        if not email or not password or not nombres or not apellidos or not rol_id:
            return jsonify({"success": False, "message": "Faltan campos", "data": None}), 400
            
        existing = query_one("SELECT id FROM public.usuarios WHERE email = %s", (email,))
        if existing:
            return jsonify({"success": False, "message": "Email ya registrado", "data": None}), 400
            
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        sql = """
            INSERT INTO public.usuarios (email, password_hash, nombres, apellidos, rol_id, sede_id, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, email, nombres, apellidos, rol_id, sede_id, estado, creado_en
        """
        row = execute_one(sql, (email, hashed_pw, nombres, apellidos, rol_id, sede_id, estado))
        return jsonify({"success": True, "message": "Usuario creado", "data": serialize(row)}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@usuarios_bp.route('/<id>', methods=['PUT'])
@require_auth
@require_roles(['admin'])
def update_usuario(id):
    try:
        data = request.json
        nombres = data.get('nombres')
        apellidos = data.get('apellidos')
        rol_id = data.get('rol_id')
        sede_id = data.get('sede_id')
        estado = data.get('estado')
        password = data.get('password')
        
        user = query_one("SELECT id FROM public.usuarios WHERE id = %s", (id,))
        if not user:
            return jsonify({"success": False, "message": "Usuario no encontrado", "data": None}), 404
            
        updates = []
        params = []
        
        if nombres:
            updates.append("nombres = %s")
            params.append(nombres)
        if apellidos:
            updates.append("apellidos = %s")
            params.append(apellidos)
        if rol_id:
            updates.append("rol_id = %s")
            params.append(rol_id)
        if 'sede_id' in data:
            updates.append("sede_id = %s")
            params.append(sede_id)
        if estado:
            updates.append("estado = %s")
            params.append(estado)
        if password:
            hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            updates.append("password_hash = %s")
            params.append(hashed_pw)
            
        if not updates:
            return jsonify({"success": False, "message": "Sin datos", "data": None}), 400
            
        updates.append("actualizado_en = NOW()")
        sql = f"UPDATE public.usuarios SET {', '.join(updates)} WHERE id = %s RETURNING id, email, nombres, apellidos, rol_id, sede_id, estado, creado_en"
        params.append(id)
        
        row = execute_one(sql, tuple(params))
        return jsonify({"success": True, "message": "Usuario actualizado", "data": serialize(row)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@usuarios_bp.route('/<id>', methods=['DELETE'])
@require_auth
@require_roles(['admin'])
def delete_usuario(id):
    try:
        user = query_one("SELECT id FROM public.usuarios WHERE id = %s", (id,))
        if not user:
            return jsonify({"success": False, "message": "Usuario no encontrado", "data": None}), 404
            
        sql = "UPDATE public.usuarios SET estado = 'inactivo', actualizado_en = NOW() WHERE id = %s RETURNING id"
        row = execute_one(sql, (id,))
        return jsonify({"success": True, "message": "Usuario desactivado", "data": serialize(row)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500
