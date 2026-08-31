import uuid
import datetime
from decimal import Decimal
from flask import Blueprint, request, jsonify
from app.db import query, query_one, execute, execute_one
from app.utils.decorators import require_auth, require_roles

sedes_bp = Blueprint('sedes', __name__, url_prefix='/api/sedes')


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


@sedes_bp.route('', methods=['GET'])
@require_auth
def get_sedes():
    try:
        estado = request.args.get('estado')
        sql = "SELECT id, nombre, direccion, ciudad, telefono, capacidad, estado, created_at, updated_at FROM public.sedes WHERE 1=1"
        params = []
        if estado:
            sql += " AND estado = %s"
            params.append(estado)
        sql += " ORDER BY nombre ASC"

        rows = query(sql, tuple(params))
        return jsonify({"success": True, "message": "Sedes obtenidas", "data": serialize(rows)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@sedes_bp.route('/<id>', methods=['GET'])
@require_auth
def get_sede(id):
    try:
        sql = "SELECT id, nombre, direccion, ciudad, telefono, capacidad, estado, created_at, updated_at FROM public.sedes WHERE id = %s"
        row = query_one(sql, (id,))
        if not row:
            return jsonify({"success": False, "message": "Sede no encontrada", "data": None}), 404
        return jsonify({"success": True, "message": "Sede obtenida", "data": serialize(row)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@sedes_bp.route('', methods=['POST'])
@require_auth
@require_roles('admin')
def create_sede():
    try:
        data = request.get_json() or {}
        nombre = (data.get('nombre') or '').strip()
        direccion = (data.get('direccion') or '').strip()
        ciudad = (data.get('ciudad') or '').strip()
        telefono = (data.get('telefono') or '').strip()
        capacidad = int(data.get('capacidad') or 0)
        estado = data.get('estado', 'activa')

        if not nombre:
            return jsonify({"success": False, "message": "El nombre de la sede es requerido", "data": None}), 400

        sql = """
            INSERT INTO public.sedes (nombre, direccion, ciudad, telefono, capacidad, estado)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, nombre, direccion, ciudad, telefono, capacidad, estado, created_at
        """
        row = execute_one(sql, (nombre, direccion, ciudad, telefono, capacidad, estado))
        return jsonify({"success": True, "message": "Sede creada exitosamente", "data": serialize(row)}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@sedes_bp.route('/<id>', methods=['PUT'])
@require_auth
@require_roles('admin')
def update_sede(id):
    try:
        data = request.get_json() or {}
        sede = query_one("SELECT id FROM public.sedes WHERE id = %s", (id,))
        if not sede:
            return jsonify({"success": False, "message": "Sede no encontrada", "data": None}), 404

        updates = []
        params = []
        for field in ['nombre', 'direccion', 'ciudad', 'telefono', 'estado']:
            if field in data:
                updates.append(f"{field} = %s")
                params.append(data[field])
        if 'capacidad' in data:
            updates.append("capacidad = %s")
            params.append(int(data['capacidad'] or 0))

        if not updates:
            return jsonify({"success": False, "message": "Sin datos para actualizar", "data": None}), 400

        updates.append("updated_at = NOW()")
        sql = f"UPDATE public.sedes SET {', '.join(updates)} WHERE id = %s RETURNING id, nombre, direccion, ciudad, telefono, capacidad, estado, created_at, updated_at"
        params.append(id)

        row = execute_one(sql, tuple(params))
        return jsonify({"success": True, "message": "Sede actualizada exitosamente", "data": serialize(row)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@sedes_bp.route('/<id>', methods=['DELETE'])
@require_auth
@require_roles('admin')
def delete_sede(id):
    try:
        sede = query_one("SELECT id FROM public.sedes WHERE id = %s", (id,))
        if not sede:
            return jsonify({"success": False, "message": "Sede no encontrada", "data": None}), 404

        sql = "UPDATE public.sedes SET estado = 'inactiva', updated_at = NOW() WHERE id = %s RETURNING id"
        row = execute_one(sql, (id,))
        return jsonify({"success": True, "message": "Sede desactivada exitosamente", "data": serialize(row)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500
