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
        sql = "SELECT id, clave, valor, descripcion, creado_en FROM public.parametros_sistema ORDER BY clave ASC"
        rows = query(sql, ())
        return jsonify({"success": True, "message": "Parámetros obtenidos", "data": serialize(rows)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@parametros_bp.route('/<clave>', methods=['GET'])
@require_auth
def get_parametro(clave):
    try:
        sql = "SELECT id, clave, valor, descripcion, creado_en FROM public.parametros_sistema WHERE clave = %s"
        row = query_one(sql, (clave,))
        if not row:
            return jsonify({"success": False, "message": "Parámetro no encontrado", "data": None}), 404
        return jsonify({"success": True, "message": "Parámetro obtenido", "data": serialize(row)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@parametros_bp.route('', methods=['POST'])
@require_auth
@require_roles(['admin'])
def create_parametro():
    try:
        data = request.json
        clave = data.get('clave')
        valor = data.get('valor')
        descripcion = data.get('descripcion')
        
        if not clave or valor is None:
            return jsonify({"success": False, "message": "Clave y valor requeridos", "data": None}), 400
            
        sql = """
            INSERT INTO public.parametros_sistema (clave, valor, descripcion)
            VALUES (%s, %s, %s)
            RETURNING id, clave, valor, descripcion, creado_en
        """
        row = execute_one(sql, (clave, valor, descripcion))
        return jsonify({"success": True, "message": "Parámetro creado", "data": serialize(row)}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@parametros_bp.route('/<clave>', methods=['PUT'])
@require_auth
@require_roles(['admin'])
def update_parametro(clave):
    try:
        data = request.json
        valor = data.get('valor')
        descripcion = data.get('descripcion')
        
        param = query_one("SELECT id FROM public.parametros_sistema WHERE clave = %s", (clave,))
        if not param:
            return jsonify({"success": False, "message": "Parámetro no encontrado", "data": None}), 404
            
        updates = []
        params = []
        if 'valor' in data:
            updates.append("valor = %s")
            params.append(valor)
        if 'descripcion' in data:
            updates.append("descripcion = %s")
            params.append(descripcion)
            
        if not updates:
            return jsonify({"success": False, "message": "Sin datos", "data": None}), 400
            
        updates.append("actualizado_en = NOW()")
        sql = f"UPDATE public.parametros_sistema SET {', '.join(updates)} WHERE clave = %s RETURNING id, clave, valor, descripcion, creado_en"
        params.append(clave)
        
        row = execute_one(sql, tuple(params))
        return jsonify({"success": True, "message": "Parámetro actualizado", "data": serialize(row)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500
