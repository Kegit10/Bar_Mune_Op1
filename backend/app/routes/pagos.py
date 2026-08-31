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

        sql = """
            SELECT p.id, p.orden_id, p.cajero_id, p.metodo_pago, p.monto_total,
                   p.monto_recibido, p.cambio, p.propina, p.numero_comprobante, p.created_at,
                   o.numero_orden, o.mesa,
                   u.nombre || ' ' || COALESCE(u.apellido, '') as cajero_nombre
            FROM public.pagos p
            JOIN public.ordenes o ON p.orden_id = o.id
            LEFT JOIN public.usuarios u ON p.cajero_id = u.id
            WHERE 1=1
        """
        params = []
        if orden_id:
            sql += " AND p.orden_id = %s"
            params.append(orden_id)
        if fecha_desde:
            sql += " AND DATE(p.created_at) >= %s"
            params.append(fecha_desde)
        if fecha_hasta:
            sql += " AND DATE(p.created_at) <= %s"
            params.append(fecha_hasta)

        sql += " ORDER BY p.created_at DESC"

        rows = query(sql, tuple(params))
        return jsonify({"success": True, "message": "Pagos obtenidos", "data": serialize(rows)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@pagos_bp.route('/<id>', methods=['GET'])
@require_auth
def get_pago(id):
    try:
        sql = """
            SELECT p.*, o.numero_orden, o.mesa, o.subtotal, o.impuesto, o.total,
                   u.nombre || ' ' || COALESCE(u.apellido, '') as cajero_nombre
            FROM public.pagos p
            JOIN public.ordenes o ON p.orden_id = o.id
            LEFT JOIN public.usuarios u ON p.cajero_id = u.id
            WHERE p.id = %s OR p.orden_id = %s
        """
        row = query_one(sql, (id, id))
        if not row:
            return jsonify({"success": False, "message": "Pago no encontrado", "data": None}), 404
        return jsonify({"success": True, "message": "Pago obtenido", "data": serialize(row)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@pagos_bp.route('', methods=['POST'])
@require_auth
@require_roles('admin', 'cajero')
def create_pago():
    try:
        data = request.get_json() or {}
        orden_id = data.get('orden_id')
        metodo_pago = (data.get('metodo_pago') or 'efectivo').lower()
        cajero_id = data.get('cajero_id')
        propina = float(data.get('propina') or 0)

        if not orden_id:
            return jsonify({"success": False, "message": "El ID de orden es requerido", "data": None}), 400

        orden = query_one("SELECT id, estado, total FROM public.ordenes WHERE id = %s", (orden_id,))
        if not orden:
            return jsonify({"success": False, "message": "Orden no encontrada", "data": None}), 404
        if orden['estado'] == 'pagada':
            return jsonify({"success": False, "message": "La orden ya ha sido pagada previamente", "data": None}), 400
        if orden['estado'] == 'cancelada':
            return jsonify({"success": False, "message": "No se puede pagar una orden cancelada", "data": None}), 400

        monto_total = float(orden['total'])
        monto_recibido = float(data.get('monto_recibido') or monto_total)
        cambio = max(0.0, round(monto_recibido - monto_total, 2))

        # Generar número de comprobante BM-YYYYMMDD-XXXXX
        hoy_str = datetime.datetime.now().strftime('%Y%m%d')
        sec = str(uuid.uuid4().hex[:6]).upper()
        numero_comprobante = f"BM-{hoy_str}-{sec}"

        sql = """
            INSERT INTO public.pagos (orden_id, cajero_id, metodo_pago, monto_total, monto_recibido, cambio, propina, numero_comprobante)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        row = execute_one(sql, (orden_id, cajero_id, metodo_pago, monto_total, monto_recibido, cambio, propina, numero_comprobante))

        # Actualizar estado de orden
        execute("UPDATE public.ordenes SET estado = 'pagada', updated_at = NOW() WHERE id = %s", (orden_id,))

        return jsonify({
            "success": True,
            "message": "Pago registrado exitosamente",
            "data": serialize(row)
        }), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500
