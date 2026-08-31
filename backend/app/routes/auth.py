from flask import Blueprint, request, jsonify
import bcrypt
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, jwt_required
from app.db import query_one, execute_one
from app.utils.decorators import require_auth

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        if not email or not password:
            return jsonify({"success": False, "message": "Email y contraseña requeridos", "data": None}), 400

        user = query_one(
            """SELECT u.*, r.nombre AS rol_nombre, s.nombre AS sede_nombre
               FROM public.usuarios u
               JOIN public.roles r ON u.rol_id = r.id
               LEFT JOIN public.sedes s ON u.sede_id = s.id
               WHERE LOWER(u.email) = %s""",
            (email,)
        )

        if not user:
            return jsonify({"success": False, "message": "Credenciales inválidas", "data": None}), 401
        if user['estado'] == 'inactivo':
            return jsonify({"success": False, "message": "Usuario inactivo", "data": None}), 403
        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return jsonify({"success": False, "message": "Credenciales inválidas", "data": None}), 401

        user_data = {
            "id":          str(user['id']),
            "email":       user['email'],
            "nombre":      user['nombre'],
            "apellido":    user['apellido'],
            "rol_id":      str(user['rol_id']),
            "rol_nombre":  user['rol_nombre'],
            "sede_id":     str(user['sede_id']) if user['sede_id'] else None,
            "sede_nombre": user['sede_nombre'],
        }
        # Flask-JWT-Extended 4.6+ requires identity to be a string
        # Store full user data in additional_claims
        token = create_access_token(
            identity=str(user['id']),
            additional_claims=user_data
        )
        return jsonify({"success": True, "message": "Login exitoso", "data": {"access_token": token, "user": user_data}}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@auth_bp.route('/me', methods=['GET'])
@require_auth
def me():
    try:
        identity = get_jwt_identity()
        user = query_one(
            """SELECT u.id, u.email, u.nombre, u.apellido, u.telefono, u.estado,
                      r.nombre AS rol_nombre, s.nombre AS sede_nombre, u.rol_id, u.sede_id
               FROM public.usuarios u
               JOIN public.roles r ON u.rol_id = r.id
               LEFT JOIN public.sedes s ON u.sede_id = s.id
               WHERE u.id = %s""",
            (identity['id'],)
        )
        if user:
            user['id'] = str(user['id'])
            user['rol_id'] = str(user['rol_id'])
            if user['sede_id']:
                user['sede_id'] = str(user['sede_id'])
        return jsonify({"success": True, "message": "Usuario obtenido", "data": user}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout():
    return jsonify({"success": True, "message": "Sesión cerrada", "data": None}), 200


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    try:
        identity = get_jwt_identity()
        token = create_access_token(identity=identity)
        return jsonify({"success": True, "message": "Token renovado", "data": {"access_token": token}}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500
