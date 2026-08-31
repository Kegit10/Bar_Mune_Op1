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
        
        sql = "SELECT id, nombre, direccion, telefono, estado, creado_en FROM public.sedes WHERE 1=1"
        params = []
        if estado:
            sql += " AND estado = %s"
            params.append(estado)
        sql += " ORDER BY creado_en DESC"
        
        rows = query(sql, tuple(params))
        return jsonify({"success": True, "message": "Sedes obtenidas", "data": serialize(rows)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@sedes_bp.route('/<id>', methods=['GET'])
@require_auth
def get_sede(id):
    try:
        sql = "SELECT id, nombre, direccion, telefono, estado, creado_en FROM public.sedes WHERE id = %s"
        row = query_one(sql, (id,))
        if not row:
            return jsonify({"success": False, "message": "Sede no encontrada", "data": None}), 404
        return jsonify({"success": True, "message": "Sede obtenida", "data": serialize(row)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@sedes_bp.route('', methods=['POST'])
@require_auth
@require_roles(['admin'])
def create_sede():
    try:
        data = request.json
        nombre = data.get('nombre')
        direccion = data.get('direccion')
        telefono = data.get('telefono')
        estado = data.get('estado', 'activa')
        
        if not nombre:
            return jsonify({"success": False, "message": "Nombre es requerido", "data": None}), 400
            
        sql = """
            INSERT INTO public.sedes (nombre, direccion, telefono, estado)
            VALUES (%s, %s, %s, %s)
            RETURNING id, nombre, direccion, telefono, estado, creado_en
        """
        row = execute_one(sql, (nombre, direccion, telefono, estado))
        return jsonify({"success": True, "message": "Sede creada", "data": serialize(row)}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@sedes_bp.route('/<id>', methods=['PUT'])
@require_auth
@require_roles(['admin'])
def update_sede(id):
    try:
        data = request.json
        
        sede = query_one("SELECT id FROM public.sedes WHERE id = %s", (id,))
        if not sede:
            return jsonify({"success": False, "message": "Sede no encontrada", "data": None}), 404
            
        updates = []
        params = []
        for field in ['nombre', 'direccion', 'telefono', 'estado']:
            if field in data:
                updates.append(f"{field} = %s")
                params.append(data[field])
                
        if not updates:
            return jsonify({"success": False, "message": "Sin datos", "data": None}), 400
            
        updates.append("actualizado_en = NOW()")
        sql = f"UPDATE public.sedes SET {', '.join(updates)} WHERE id = %s RETURNING id, nombre, direccion, telefono, estado, creado_en"
        params.append(id)
        
        row = execute_one(sql, tuple(params))
        return jsonify({"success": True, "message": "Sede actualizada", "data": serialize(row)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@sedes_bp.route('/<id>', methods=['DELETE'])
@require_auth
@require_roles(['admin'])
def delete_sede(id):
    try:
        sede = query_one("SELECT id FROM public.sedes WHERE id = %s", (id,))
        if not sede:
            return jsonify({"success": False, "message": "Sede no encontrada", "data": None}), 404
            
        sql = "UPDATE public.sedes SET estado = 'inactiva', actualizado_en = NOW() WHERE id = %s RETURNING id"
        row = execute_one(sql, (id,))
        return jsonify({"success": True, "message": "Sede desactivada", "data": serialize(row)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500
