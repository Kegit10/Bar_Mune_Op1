from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import get_jwt, verify_jwt_in_request


def require_auth(f):
    """Verifica que el request tenga un JWT válido."""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception as e:
            return jsonify({"success": False, "message": "Autenticación requerida", "data": None}), 401
        return f(*args, **kwargs)
    return decorated


def require_roles(*roles):
    """Verifica JWT y que el rol del usuario esté en la lista permitida.
    Lee rol_nombre desde los additional_claims del JWT (sin llamar a la BD).
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            try:
                verify_jwt_in_request()
                claims = get_jwt()  # Contiene additional_claims: rol_nombre, email, etc.
                user_role = (claims.get('rol_nombre') or '').lower()
                allowed = [r.lower() for r in roles]
                if user_role not in allowed:
                    return jsonify({
                        "success": False,
                        "message": f"Acceso denegado. Roles permitidos: {list(roles)}",
                        "data": None
                    }), 403
            except Exception as e:
                return jsonify({"success": False, "message": "Autenticación requerida", "data": None}), 401
            return f(*args, **kwargs)
        return decorated
    return decorator


def get_current_user():
    """Helper: retorna los claims del usuario del JWT actual."""
    return get_jwt()
