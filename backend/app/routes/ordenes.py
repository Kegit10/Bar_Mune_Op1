import uuid
import datetime
from decimal import Decimal
from flask import Blueprint, request, jsonify
from app.db import query, query_one, execute, execute_one
from app.utils.decorators import require_auth, require_roles

ordenes_bp = Blueprint('ordenes', __name__, url_prefix='/api/ordenes')


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


def recalculate_order(orden_id):
    """Recalcula subtotal, impuesto y total de la orden según sus items."""
    result = query_one(
        "SELECT COALESCE(SUM(subtotal), 0) AS subtotal FROM public.orden_items WHERE orden_id = %s",
        (orden_id,)
    )
    subtotal = float(result['subtotal']) if result else 0.0

    param = query_one("SELECT valor FROM public.parametros_sistema WHERE clave = 'impuesto_porcentaje'")
    try:
        pct = float(param['valor']) if param else 19.0
    except Exception:
        pct = 19.0

    impuesto = round(subtotal * (pct / 100.0), 2)
    total = round(subtotal + impuesto, 2)

    execute(
        "UPDATE public.ordenes SET subtotal = %s, impuesto = %s, total = %s, updated_at = NOW() WHERE id = %s",
        (subtotal, impuesto, total, orden_id)
    )
    return {"subtotal": subtotal, "impuesto": impuesto, "total": total}


@ordenes_bp.route('', methods=['GET'])
@require_auth
def get_ordenes():
    try:
        estado = request.args.get('estado')
        sede_id = request.args.get('sede_id')
        mesero_id = request.args.get('mesero_id')
        fecha = request.args.get('fecha')

        sql = """
            SELECT o.id, o.numero_orden, o.mesa, o.sede_id, o.mesero_id, o.estado,
                   o.subtotal, o.impuesto, o.total, o.notas, o.created_at, o.updated_at,
                   s.nombre as sede_nombre,
                   u.nombre || ' ' || COALESCE(u.apellido, '') as mesero_nombre
            FROM public.ordenes o
            LEFT JOIN public.sedes s ON o.sede_id = s.id
            LEFT JOIN public.usuarios u ON o.mesero_id = u.id
            WHERE 1=1
        """
        params = []

        if estado:
            estados = [e.strip() for e in estado.split(',') if e.strip()]
            if len(estados) == 1:
                sql += " AND o.estado = %s"
                params.append(estados[0])
            elif len(estados) > 1:
                placeholders = ', '.join(['%s'] * len(estados))
                sql += f" AND o.estado IN ({placeholders})"
                params.extend(estados)

        if sede_id:
            sql += " AND o.sede_id = %s"
            params.append(sede_id)
        if mesero_id:
            sql += " AND o.mesero_id = %s"
            params.append(mesero_id)
        if fecha:
            sql += " AND DATE(o.created_at) = %s"
            params.append(fecha)

        sql += " ORDER BY o.created_at DESC"

        rows = query(sql, tuple(params))
        return jsonify({"success": True, "message": "Órdenes obtenidas", "data": serialize(rows)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@ordenes_bp.route('/<id>', methods=['GET'])
@require_auth
def get_orden(id):
    try:
        orden = query_one(
            """SELECT o.id, o.numero_orden, o.mesa, o.sede_id, o.mesero_id, o.estado,
                      o.subtotal, o.impuesto, o.total, o.notas, o.created_at, o.updated_at,
                      s.nombre as sede_nombre,
                      u.nombre || ' ' || COALESCE(u.apellido, '') as mesero_nombre
               FROM public.ordenes o
               LEFT JOIN public.sedes s ON o.sede_id = s.id
               LEFT JOIN public.usuarios u ON o.mesero_id = u.id
               WHERE o.id = %s""",
            (id,)
        )
        if not orden:
            return jsonify({"success": False, "message": "Orden no encontrada", "data": None}), 404

        items = query(
            """SELECT oi.id, oi.orden_id, oi.producto_id, oi.cantidad, oi.precio_unitario,
                      oi.subtotal, oi.notas, oi.created_at,
                      p.nombre as producto_nombre, p.codigo as producto_codigo
               FROM public.orden_items oi
               JOIN public.productos p ON oi.producto_id = p.id
               WHERE oi.orden_id = %s
               ORDER BY oi.created_at ASC""",
            (id,)
        )

        pago = query_one(
            "SELECT id, metodo_pago, monto_total, monto_recibido, cambio, propina, numero_comprobante, created_at FROM public.pagos WHERE orden_id = %s",
            (id,)
        )

        data = serialize(orden)
        data['items'] = serialize(items)
        data['pago'] = serialize(pago)
        return jsonify({"success": True, "message": "Detalle de orden obtenido", "data": data}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@ordenes_bp.route('', methods=['POST'])
@require_auth
def create_orden():
    try:
        data = request.get_json() or {}
        mesa = str(data.get('mesa', '')).strip()
        sede_id = data.get('sede_id')
        mesero_id = data.get('mesero_id')
        notas = data.get('notas', '')

        if not mesa:
            return jsonify({"success": False, "message": "El número o identificador de mesa es requerido", "data": None}), 400

        # Si no se pasó sede_id, buscar la primera sede activa
        if not sede_id:
            first_sede = query_one("SELECT id FROM public.sedes WHERE estado = 'activa' LIMIT 1")
            sede_id = first_sede['id'] if first_sede else None

        sql = """
            INSERT INTO public.ordenes (mesa, sede_id, mesero_id, notas, estado, subtotal, impuesto, total)
            VALUES (%s, %s, %s, %s, 'abierta', 0, 0, 0)
            RETURNING *
        """
        row = execute_one(sql, (mesa, sede_id, mesero_id, notas))
        return jsonify({"success": True, "message": "Orden creada exitosamente", "data": serialize(row)}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@ordenes_bp.route('/<id>', methods=['PUT'])
@require_auth
def update_orden(id):
    try:
        data = request.get_json() or {}
        orden = query_one("SELECT id, estado FROM public.ordenes WHERE id = %s", (id,))
        if not orden:
            return jsonify({"success": False, "message": "Orden no encontrada", "data": None}), 404

        updates = []
        params = []
        if 'estado' in data:
            updates.append("estado = %s")
            params.append(data['estado'])
        if 'mesa' in data:
            updates.append("mesa = %s")
            params.append(str(data['mesa']))
        if 'notas' in data:
            updates.append("notas = %s")
            params.append(data['notas'])

        if not updates:
            return jsonify({"success": False, "message": "Sin datos para actualizar", "data": None}), 400

        updates.append("updated_at = NOW()")
        sql = f"UPDATE public.ordenes SET {', '.join(updates)} WHERE id = %s RETURNING *"
        params.append(id)

        row = execute_one(sql, tuple(params))
        return jsonify({"success": True, "message": "Orden actualizada", "data": serialize(row)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@ordenes_bp.route('/<id>/items', methods=['POST'])
@require_auth
def add_items(id):
    try:
        orden = query_one("SELECT id, estado FROM public.ordenes WHERE id = %s", (id,))
        if not orden:
            return jsonify({"success": False, "message": "Orden no encontrada", "data": None}), 404
        if orden['estado'] in ['pagada', 'cancelada']:
            return jsonify({"success": False, "message": f"No se pueden agregar items a una orden {orden['estado']}", "data": None}), 400

        data = request.get_json() or {}
        items = data.get('items') or [data] if not isinstance(data, list) else data

        inserted_items = []
        for item in items:
            producto_id = item.get('producto_id')
            cantidad = int(item.get('cantidad', 1))
            notas = item.get('notas', '')

            if not producto_id or cantidad <= 0:
                continue

            prod = query_one("SELECT id, precio_venta, stock_actual, nombre FROM public.productos WHERE id = %s", (producto_id,))
            if not prod:
                continue

            precio_unitario = float(item.get('precio_unitario') or prod['precio_venta'])
            subtotal_item = round(cantidad * precio_unitario, 2)

            # Insertar item
            item_row = execute_one(
                """INSERT INTO public.orden_items (orden_id, producto_id, cantidad, precio_unitario, subtotal, notas)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (id, producto_id, cantidad, precio_unitario, subtotal_item, notas)
            )
            inserted_items.append(item_row)

            # Descontar inventario
            nuevo_stock = max(0, int(prod['stock_actual']) - cantidad)
            execute("UPDATE public.productos SET stock_actual = %s, updated_at = NOW() WHERE id = %s", (nuevo_stock, producto_id))

            # Registrar movimiento
            execute(
                """INSERT INTO public.movimientos_inventario (producto_id, tipo, cantidad, stock_anterior, stock_nuevo, referencia)
                   VALUES (%s, 'salida', %s, %s, %s, %s)""",
                (producto_id, cantidad, prod['stock_actual'], nuevo_stock, f"Orden #{id[:8]}")
            )

        # Si la orden estaba abierta, pasar a en_proceso
        if orden['estado'] == 'abierta':
            execute("UPDATE public.ordenes SET estado = 'en_proceso' WHERE id = %s", (id,))

        totals = recalculate_order(id)
        return jsonify({
            "success": True,
            "message": "Items agregados exitosamente",
            "data": {
                "items": serialize(inserted_items),
                "totales": totals
            }
        }), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@ordenes_bp.route('/<id>/items/<item_id>', methods=['DELETE'])
@require_auth
def remove_item(id, item_id):
    try:
        item = query_one("SELECT id, producto_id, cantidad FROM public.orden_items WHERE id = %s AND orden_id = %s", (item_id, id))
        if not item:
            return jsonify({"success": False, "message": "Item no encontrado", "data": None}), 404

        # Restaurar stock
        prod = query_one("SELECT id, stock_actual FROM public.productos WHERE id = %s", (item['producto_id'],))
        if prod:
            nuevo_stock = int(prod['stock_actual']) + int(item['cantidad'])
            execute("UPDATE public.productos SET stock_actual = %s, updated_at = NOW() WHERE id = %s", (nuevo_stock, item['producto_id']))
            execute(
                """INSERT INTO public.movimientos_inventario (producto_id, tipo, cantidad, stock_anterior, stock_nuevo, referencia)
                   VALUES (%s, 'entrada', %s, %s, %s, %s)""",
                (item['producto_id'], item['cantidad'], prod['stock_actual'], nuevo_stock, f"Cancelación item orden #{id[:8]}")
            )

        execute("DELETE FROM public.orden_items WHERE id = %s", (item_id,))
        totals = recalculate_order(id)
        return jsonify({"success": True, "message": "Item eliminado y stock restaurado", "data": totals}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@ordenes_bp.route('/<id>', methods=['DELETE'])
@require_auth
def cancel_orden(id):
    try:
        orden = query_one("SELECT id, estado FROM public.ordenes WHERE id = %s", (id,))
        if not orden:
            return jsonify({"success": False, "message": "Orden no encontrada", "data": None}), 404

        # Restaurar stock de todos los items
        items = query("SELECT producto_id, cantidad FROM public.orden_items WHERE orden_id = %s", (id,))
        for it in items:
            prod = query_one("SELECT id, stock_actual FROM public.productos WHERE id = %s", (it['producto_id'],))
            if prod:
                nuevo_stock = int(prod['stock_actual']) + int(it['cantidad'])
                execute("UPDATE public.productos SET stock_actual = %s WHERE id = %s", (nuevo_stock, it['producto_id']))

        execute("UPDATE public.ordenes SET estado = 'cancelada', updated_at = NOW() WHERE id = %s", (id,))
        return jsonify({"success": True, "message": "Orden cancelada y stock restaurado", "data": None}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500
