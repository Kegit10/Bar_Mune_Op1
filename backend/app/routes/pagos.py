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
        sede_id = request.args.get('sede_id')
        fecha_desde = request.args.get('fecha_desde')
        fecha_hasta = request.args.get('fecha_hasta')

        sql = """
            SELECT p.id, p.orden_id, p.cajero_id, p.metodo_pago, p.monto_total,
                   p.monto_recibido, p.cambio, p.propina, p.numero_comprobante, p.created_at,
                   COALESCE(p.cliente_nombre, 'Consumidor Final') as cliente_nombre,
                   COALESCE(p.cliente_documento, '222222222222') as cliente_documento,
                   p.cliente_telefono, p.cliente_email,
                   o.numero_orden, o.mesa, o.subtotal, o.impuesto, o.total,
                   s.nombre as sede_nombre, s.direccion as sede_direccion, s.ciudad as sede_ciudad, s.telefono as sede_telefono,
                   u.nombre || ' ' || COALESCE(u.apellido, '') as cajero_nombre,
                   m.nombre || ' ' || COALESCE(m.apellido, '') as mesero_nombre
            FROM public.pagos p
            JOIN public.ordenes o ON p.orden_id = o.id
            LEFT JOIN public.sedes s ON o.sede_id = s.id
            LEFT JOIN public.usuarios u ON p.cajero_id = u.id
            LEFT JOIN public.usuarios m ON o.mesero_id = m.id
            WHERE 1=1
        """
        params = []
        if orden_id:
            sql += " AND p.orden_id = %s"
            params.append(orden_id)
        if sede_id:
            sql += " AND o.sede_id = %s"
            params.append(sede_id)
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


@pagos_bp.route('/<identifier>', methods=['GET'])
@require_auth
def get_pago_detail(identifier):
    """Obtiene el detalle completo de un pago/factura por ID, orden_id o numero_comprobante."""
    try:
        sql = """
            SELECT p.id, p.orden_id, p.cajero_id, p.metodo_pago, p.monto_total,
                   p.monto_recibido, p.cambio, p.propina, p.numero_comprobante, p.created_at,
                   COALESCE(p.cliente_nombre, 'Consumidor Final') as cliente_nombre,
                   COALESCE(p.cliente_documento, '222222222222') as cliente_documento,
                   p.cliente_telefono, p.cliente_email,
                   o.numero_orden, o.mesa, o.subtotal, o.impuesto, o.total,
                   s.nombre as sede_nombre, s.direccion as sede_direccion, s.ciudad as sede_ciudad, s.telefono as sede_telefono,
                   u.nombre || ' ' || COALESCE(u.apellido, '') as cajero_nombre,
                   m.nombre || ' ' || COALESCE(m.apellido, '') as mesero_nombre
            FROM public.pagos p
            JOIN public.ordenes o ON p.orden_id = o.id
            LEFT JOIN public.sedes s ON o.sede_id = s.id
            LEFT JOIN public.usuarios u ON p.cajero_id = u.id
            LEFT JOIN public.usuarios m ON o.mesero_id = m.id
            WHERE p.id::text = %s OR p.orden_id::text = %s OR p.numero_comprobante = %s
        """
        row = query_one(sql, (identifier, identifier, identifier))
        if not row:
            return jsonify({"success": False, "message": "Factura o pago no encontrado", "data": None}), 404

        data = serialize(row)

        # Consultar porcentaje de impuesto del sistema
        param_tax = query_one("SELECT valor FROM public.parametros_sistema WHERE clave = 'impuesto_porcentaje'")
        tax_pct = float(param_tax['valor']) if param_tax else 19.0

        param_nit = query_one("SELECT valor FROM public.parametros_sistema WHERE clave = 'empresa_nit'")
        data['nit'] = param_nit['valor'] if param_nit else '900.123.456-7'

        param_razon = query_one("SELECT valor FROM public.parametros_sistema WHERE clave = 'empresa_razon_social'")
        data['razon_social'] = param_razon['valor'] if param_razon else 'Bar Luné S.A.S.'

        # Consultar items de la orden
        items_sql = """
            SELECT oi.id, oi.cantidad, oi.precio_unitario, oi.subtotal,
                   p.nombre as producto_nombre, p.codigo as producto_codigo
            FROM public.orden_items oi
            JOIN public.productos p ON oi.producto_id = p.id
            WHERE oi.orden_id = %s
            ORDER BY oi.created_at ASC
        """
        raw_items = query(items_sql, (data['orden_id'],))
        items = []
        for it in raw_items:
            qty = float(it['cantidad'])
            unit_p = float(it['precio_unitario'])
            item_sub = float(it['subtotal'])
            item_tax = round(item_sub * (tax_pct / 100.0), 2)
            item_total = round(item_sub + item_tax, 2)

            items.append({
                "id": str(it['id']),
                "cantidad": int(qty) if qty.is_integer() else qty,
                "producto_nombre": it['producto_nombre'],
                "producto_codigo": it['producto_codigo'],
                "precio_unitario": unit_p,
                "subtotal": item_sub,
                "impuesto": item_tax,
                "total": item_total
            })

        data['items'] = items
        data['tax_pct'] = tax_pct

        return jsonify({"success": True, "message": "Detalle de factura obtenido", "data": data}), 200
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
        cliente_nombre = (data.get('cliente_nombre') or 'Consumidor Final').strip()
        cliente_documento = (data.get('cliente_documento') or '222222222222').strip()
        cliente_telefono = (data.get('cliente_telefono') or '').strip()
        cliente_email = (data.get('cliente_email') or '').strip()

        if not orden_id:
            return jsonify({"success": False, "message": "El ID de orden es requerido", "data": None}), 400

        orden = query_one("SELECT id, estado, total, subtotal, impuesto, mesa, sede_id FROM public.ordenes WHERE id = %s", (orden_id,))
        if not orden:
            return jsonify({"success": False, "message": "Orden no encontrada", "data": None}), 404
        if orden['estado'] == 'pagada':
            return jsonify({"success": False, "message": "La orden ya ha sido pagada previamente", "data": None}), 400
        if orden['estado'] == 'cancelada':
            return jsonify({"success": False, "message": "No se puede pagar una orden cancelada", "data": None}), 400

        # Validar que la orden tenga al menos un producto
        items_count = query_one("SELECT COUNT(*) as count FROM public.orden_items WHERE orden_id = %s", (orden_id,))
        if not items_count or int(items_count['count']) == 0:
            return jsonify({"success": False, "message": "No se puede registrar el pago de una orden sin productos", "data": None}), 400

        total_con_propina = round(float(orden['total']) + propina, 2)
        monto_recibido = float(data.get('monto_recibido') or total_con_propina)
        cambio = max(0.0, round(monto_recibido - total_con_propina, 2))

        # Generar número de comprobante BM-YYYYMMDD-XXXXX
        hoy_str = datetime.datetime.now().strftime('%Y%m%d')
        sec = str(uuid.uuid4().hex[:6]).upper()
        numero_comprobante = f"BM-{hoy_str}-{sec}"

        sql = """
            INSERT INTO public.pagos (
                orden_id, cajero_id, metodo_pago, monto_total, monto_recibido, cambio, propina, numero_comprobante,
                cliente_nombre, cliente_documento, cliente_telefono, cliente_email
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        row = execute_one(sql, (
            orden_id, cajero_id, metodo_pago, total_con_propina, monto_recibido, cambio, propina, numero_comprobante,
            cliente_nombre, cliente_documento, cliente_telefono, cliente_email
        ))

        # Actualizar estado y datos del cliente en orden
        execute("""
            UPDATE public.ordenes 
            SET estado = 'pagada', 
                cliente_nombre = %s, 
                cliente_documento = %s, 
                updated_at = NOW() 
            WHERE id = %s
        """, (cliente_nombre, cliente_documento, orden_id))

        return jsonify({
            "success": True,
            "message": "Pago registrado y factura generada exitosamente",
            "data": serialize(row)
        }), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500
