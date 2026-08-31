import uuid
import datetime
from decimal import Decimal
from flask import Blueprint, request, jsonify
from app.db import query, query_one, execute, execute_one
from app.utils.decorators import require_auth, require_roles

parametros_bp = Blueprint('parametros', __name__, url_prefix='/api/parametros')


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


@parametros_bp.route('', methods=['GET'])
@require_auth
def get_parametros():
    try:
        sql = "SELECT id, clave, valor, descripcion, tipo, categoria, updated_at FROM public.parametros_sistema ORDER BY categoria, clave ASC"
        rows = query(sql, ())
        return jsonify({"success": True, "message": "Parámetros obtenidos", "data": serialize(rows)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@parametros_bp.route('/<identificador>', methods=['GET'])
@require_auth
def get_parametro(identificador):
    try:
        # Puede ser id (UUID) o clave (string)
        sql = "SELECT id, clave, valor, descripcion, tipo, categoria, updated_at FROM public.parametros_sistema WHERE clave = %s OR id::text = %s"
        row = query_one(sql, (identificador, identificador))
        if not row:
            return jsonify({"success": False, "message": "Parámetro no encontrado", "data": None}), 404
        return jsonify({"success": True, "message": "Parámetro obtenido", "data": serialize(row)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@parametros_bp.route('', methods=['POST'])
@require_auth
@require_roles('admin')
def create_parametro():
    try:
        data = request.get_json() or {}
        clave = (data.get('clave') or '').strip()
        valor = str(data.get('valor', '')).strip()
        descripcion = data.get('descripcion', '')
        tipo = data.get('tipo', 'string')
        categoria = data.get('categoria', 'general')

        if not clave:
            return jsonify({"success": False, "message": "La clave del parámetro es requerida", "data": None}), 400

        existing = query_one("SELECT id FROM public.parametros_sistema WHERE clave = %s", (clave,))
        if existing:
            return jsonify({"success": False, "message": f"El parámetro '{clave}' ya existe", "data": None}), 400

        sql = """
            INSERT INTO public.parametros_sistema (clave, valor, descripcion, tipo, categoria)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, clave, valor, descripcion, tipo, categoria, updated_at
        """
        row = execute_one(sql, (clave, valor, descripcion, tipo, categoria))
        return jsonify({"success": True, "message": "Parámetro creado", "data": serialize(row)}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@parametros_bp.route('/<identificador>', methods=['PUT'])
@require_auth
@require_roles('admin')
def update_parametro(identificador):
    try:
        data = request.get_json() or {}
        param = query_one("SELECT id, clave FROM public.parametros_sistema WHERE clave = %s OR id::text = %s", (identificador, identificador))
        if not param:
            return jsonify({"success": False, "message": "Parámetro no encontrado", "data": None}), 404

        updates = []
        params = []
        if 'valor' in data:
            updates.append("valor = %s")
            params.append(str(data['valor']))
        if 'descripcion' in data:
            updates.append("descripcion = %s")
            params.append(data['descripcion'])
        if 'categoria' in data:
            updates.append("categoria = %s")
            params.append(data['categoria'])
        if 'tipo' in data:
            updates.append("tipo = %s")
            params.append(data['tipo'])

        if not updates:
            return jsonify({"success": False, "message": "Sin datos para actualizar", "data": None}), 400

        updates.append("updated_at = NOW()")
        sql = f"UPDATE public.parametros_sistema SET {', '.join(updates)} WHERE id = %s RETURNING id, clave, valor, descripcion, tipo, categoria, updated_at"
        params.append(param['id'])

        row = execute_one(sql, tuple(params))
        return jsonify({"success": True, "message": "Parámetro actualizado exitosamente", "data": serialize(row)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500
