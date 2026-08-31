import uuid
import datetime
from decimal import Decimal
from flask import Blueprint, request, jsonify
from app.db import query, query_one, execute, execute_one
from app.utils.decorators import require_auth, require_roles

pagos_bp = Blueprint('pagos', __name__, url_prefix='/api/pagos')

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

@pagos_bp.route('', methods=['GET'])
@require_auth
def get_pagos():
    try:
        orden_id = request.args.get('orden_id')
        fecha_desde = request.args.get('fecha_desde')
        fecha_hasta = request.args.get('fecha_hasta')
        
        sql = "SELECT * FROM public.pagos WHERE 1=1"
        params = []
        if orden_id:
            sql += " AND orden_id = %s"
            params.append(orden_id)
        if fecha_desde:
            sql += " AND DATE(creado_en) >= %s"
            params.append(fecha_desde)
        if fecha_hasta:
            sql += " AND DATE(creado_en) <= %s"
            params.append(fecha_hasta)
            
        sql += " ORDER BY creado_en DESC"
        
        rows = query(sql, tuple(params))
        return jsonify({"success": True, "message": "Pagos obtenidos", "data": serialize(rows)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@pagos_bp.route('/<id>', methods=['GET'])
@require_auth
def get_pago(id):
    try:
        sql = "SELECT * FROM public.pagos WHERE id = %s"
        row = query_one(sql, (id,))
        if not row:
            return jsonify({"success": False, "message": "Pago no encontrado", "data": None}), 404
        return jsonify({"success": True, "message": "Pago obtenido", "data": serialize(row)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@pagos_bp.route('', methods=['POST'])
@require_auth
def create_pago():
    try:
        data = request.json
        orden_id = data.get('orden_id')
        metodo_pago = data.get('metodo_pago')
        monto_recibido = data.get('monto_recibido')
        propina = data.get('propina', 0)
        
        if not orden_id or not metodo_pago:
            return jsonify({"success": False, "message": "Faltan campos", "data": None}), 400
            
        orden = query_one("SELECT * FROM public.ordenes WHERE id = %s", (orden_id,))
        if not orden:
            return jsonify({"success": False, "message": "Orden no encontrada", "data": None}), 404
            
        if orden['estado'] in ['pagada', 'cancelada']:
            return jsonify({"success": False, "message": f"Orden ya está {orden['estado']}", "data": None}), 400
            
        if monto_recibido is None:
            monto_recibido = orden['total']
            
        hoy = datetime.datetime.now()
        fecha_str = hoy.strftime('%Y%m%d')
        sec = str(uuid.uuid4().int)[:5]
        comprobante = f"BM-{fecha_str}-{sec}"
        
        sql = """
            INSERT INTO public.pagos (orden_id, metodo_pago, monto_recibido, propina, comprobante)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *
        """
        row = execute_one(sql, (orden_id, metodo_pago, monto_recibido, propina, comprobante))
        
        execute("UPDATE public.ordenes SET estado = 'pagada', actualizado_en = NOW() WHERE id = %s", (orden_id,))
        
        return jsonify({"success": True, "message": "Pago registrado", "data": serialize(row)}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500
