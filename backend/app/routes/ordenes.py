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
    result = query_one('SELECT COALESCE(SUM(cantidad * precio_unitario), 0) AS subtotal FROM public.orden_items WHERE orden_id = %s', (orden_id,))
    subtotal = float(result['subtotal']) if result else 0.0
    param = query_one("SELECT valor FROM public.parametros_sistema WHERE clave = 'impuesto_porcentaje'")
    pct = float(param['valor']) if param else 19.0
    impuesto = round(subtotal * pct / 100, 2)
    total = subtotal + impuesto
    execute('UPDATE public.ordenes SET subtotal=%s, impuesto=%s, total=%s, actualizado_en=NOW() WHERE id=%s', (subtotal, impuesto, total, orden_id))

@ordenes_bp.route('', methods=['GET'])
@require_auth
def get_ordenes():
    try:
        estado = request.args.get('estado')
        sede_id = request.args.get('sede_id')
        mesero_id = request.args.get('mesero_id')
        fecha = request.args.get('fecha')
        
        sql = "SELECT * FROM public.ordenes WHERE 1=1"
        params = []
        if estado:
            sql += " AND estado = %s"
            params.append(estado)
        if sede_id:
            sql += " AND sede_id = %s"
            params.append(sede_id)
        if mesero_id:
            sql += " AND mesero_id = %s"
            params.append(mesero_id)
        if fecha:
            sql += " AND DATE(creado_en) = %s"
            params.append(fecha)
            
        sql += " ORDER BY creado_en DESC"
        
        rows = query(sql, tuple(params))
        return jsonify({"success": True, "message": "Órdenes obtenidas", "data": serialize(rows)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@ordenes_bp.route('/<id>', methods=['GET'])
@require_auth
def get_orden(id):
    try:
        orden = query_one("SELECT * FROM public.ordenes WHERE id = %s", (id,))
        if not orden:
            return jsonify({"success": False, "message": "Orden no encontrada", "data": None}), 404
            
        items_sql = """
            SELECT i.*, p.nombre as producto_nombre, p.codigo as producto_codigo
            FROM public.orden_items i
            JOIN public.productos p ON i.producto_id = p.id
            WHERE i.orden_id = %s
        """
        items = query(items_sql, (id,))
        orden['items'] = items
        
        return jsonify({"success": True, "message": "Orden obtenida", "data": serialize(orden)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@ordenes_bp.route('', methods=['POST'])
@require_auth
def create_orden():
    try:
        data = request.json
        mesa = data.get('mesa')
        sede_id = data.get('sede_id')
        mesero_id = data.get('mesero_id')
        notas = data.get('notas')
        
        if not mesa or not sede_id:
            return jsonify({"success": False, "message": "Faltan campos mesa y sede_id", "data": None}), 400
            
        sql = """
            INSERT INTO public.ordenes (mesa, sede_id, mesero_id, notas, estado, subtotal, impuesto, total)
            VALUES (%s, %s, %s, %s, 'abierta', 0, 0, 0)
            RETURNING *
        """
        row = execute_one(sql, (mesa, sede_id, mesero_id, notas))
        return jsonify({"success": True, "message": "Orden creada", "data": serialize(row)}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@ordenes_bp.route('/<id>', methods=['PUT'])
@require_auth
def update_orden(id):
    try:
        data = request.json
        
        orden = query_one("SELECT id FROM public.ordenes WHERE id = %s", (id,))
        if not orden:
            return jsonify({"success": False, "message": "Orden no encontrada", "data": None}), 404
            
        updates = []
        params = []
        if 'estado' in data:
            updates.append("estado = %s")
            params.append(data['estado'])
        if 'notas' in data:
            updates.append("notas = %s")
            params.append(data['notas'])
            
        if not updates:
            return jsonify({"success": False, "message": "Sin datos", "data": None}), 400
            
        updates.append("actualizado_en = NOW()")
        sql = f"UPDATE public.ordenes SET {', '.join(updates)} WHERE id = %s RETURNING *"
        params.append(id)
        
        row = execute_one(sql, tuple(params))
        return jsonify({"success": True, "message": "Orden actualizada", "data": serialize(row)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@ordenes_bp.route('/<id>/items', methods=['POST'])
@require_auth
def add_orden_item(id):
    try:
        data = request.json
        if not isinstance(data, list):
            data = [data]
            
        orden = query_one("SELECT * FROM public.ordenes WHERE id = %s", (id,))
        if not orden:
            return jsonify({"success": False, "message": "Orden no encontrada", "data": None}), 404
            
        added_items = []
        for item in data:
            prod_id = item.get('producto_id')
            cant = int(item.get('cantidad', 1))
            notas = item.get('notas')
            
            prod = query_one("SELECT * FROM public.productos WHERE id = %s", (prod_id,))
            if not prod:
                continue
                
            precio_unitario = item.get('precio_unitario', prod['precio'])
            
            if prod['stock_actual'] < cant:
                return jsonify({"success": False, "message": f"Stock insuficiente para {prod['nombre']}", "data": None}), 400
                
            execute("UPDATE public.productos SET stock_actual = stock_actual - %s WHERE id = %s", (cant, prod_id))
            
            mov_sql = """
                INSERT INTO public.movimientos_inventario (producto_id, sede_id, tipo_movimiento, cantidad, motivo)
                VALUES (%s, %s, 'salida', %s, %s)
            """
            execute(mov_sql, (prod_id, orden['sede_id'], cant, f"Venta orden {id}"))
            
            ins_sql = """
                INSERT INTO public.orden_items (orden_id, producto_id, cantidad, precio_unitario, notas)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
            """
            new_item = execute_one(ins_sql, (id, prod_id, cant, precio_unitario, notas))
            added_items.append(new_item)
            
        execute("UPDATE public.ordenes SET estado = 'en_proceso' WHERE id = %s", (id,))
        recalculate_order(id)
        
        return jsonify({"success": True, "message": "Items agregados", "data": serialize(added_items)}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@ordenes_bp.route('/<id>/items/<item_id>', methods=['DELETE'])
@require_auth
def delete_orden_item(id, item_id):
    try:
        orden = query_one("SELECT * FROM public.ordenes WHERE id = %s", (id,))
        item = query_one("SELECT * FROM public.orden_items WHERE id = %s AND orden_id = %s", (item_id, id))
        
        if not item or not orden:
            return jsonify({"success": False, "message": "Item u orden no encontrados", "data": None}), 404
            
        execute("UPDATE public.productos SET stock_actual = stock_actual + %s WHERE id = %s", (item['cantidad'], item['producto_id']))
        
        mov_sql = """
            INSERT INTO public.movimientos_inventario (producto_id, sede_id, tipo_movimiento, cantidad, motivo)
            VALUES (%s, %s, 'entrada', %s, %s)
        """
        execute(mov_sql, (item['producto_id'], orden['sede_id'], item['cantidad'], f"Cancelacion item de orden {id}"))
        
        execute("DELETE FROM public.orden_items WHERE id = %s", (item_id,))
        
        recalculate_order(id)
        return jsonify({"success": True, "message": "Item eliminado", "data": None}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@ordenes_bp.route('/<id>/items/<item_id>', methods=['PUT'])
@require_auth
def update_orden_item(id, item_id):
    try:
        data = request.json
        nueva_cantidad = int(data.get('cantidad', 0))
        
        if nueva_cantidad <= 0:
            return jsonify({"success": False, "message": "Cantidad invalida", "data": None}), 400
            
        orden = query_one("SELECT * FROM public.ordenes WHERE id = %s", (id,))
        item = query_one("SELECT * FROM public.orden_items WHERE id = %s AND orden_id = %s", (item_id, id))
        
        if not item or not orden:
            return jsonify({"success": False, "message": "Item u orden no encontrados", "data": None}), 404
            
        diff = nueva_cantidad - item['cantidad']
        
        if diff > 0:
            prod = query_one("SELECT stock_actual FROM public.productos WHERE id = %s", (item['producto_id'],))
            if prod['stock_actual'] < diff:
                return jsonify({"success": False, "message": "Stock insuficiente", "data": None}), 400
            execute("UPDATE public.productos SET stock_actual = stock_actual - %s WHERE id = %s", (diff, item['producto_id']))
            tipo_mov = 'salida'
            cant_mov = diff
        elif diff < 0:
            cant_abs = abs(diff)
            execute("UPDATE public.productos SET stock_actual = stock_actual + %s WHERE id = %s", (cant_abs, item['producto_id']))
            tipo_mov = 'entrada'
            cant_mov = cant_abs
            
        if diff != 0:
            mov_sql = """
                INSERT INTO public.movimientos_inventario (producto_id, sede_id, tipo_movimiento, cantidad, motivo)
                VALUES (%s, %s, %s, %s, %s)
            """
            execute(mov_sql, (item['producto_id'], orden['sede_id'], tipo_mov, cant_mov, f"Ajuste item orden {id}"))
            
            execute("UPDATE public.orden_items SET cantidad = %s WHERE id = %s", (nueva_cantidad, item_id))
            recalculate_order(id)
            
        return jsonify({"success": True, "message": "Item actualizado", "data": None}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@ordenes_bp.route('/<id>', methods=['DELETE'])
@require_auth
def cancel_orden(id):
    try:
        orden = query_one("SELECT * FROM public.ordenes WHERE id = %s", (id,))
        if not orden:
            return jsonify({"success": False, "message": "Orden no encontrada", "data": None}), 404
            
        items = query("SELECT * FROM public.orden_items WHERE orden_id = %s", (id,))
        
        for item in items:
            execute("UPDATE public.productos SET stock_actual = stock_actual + %s WHERE id = %s", (item['cantidad'], item['producto_id']))
            mov_sql = """
                INSERT INTO public.movimientos_inventario (producto_id, sede_id, tipo_movimiento, cantidad, motivo)
                VALUES (%s, %s, 'entrada', %s, %s)
            """
            execute(mov_sql, (item['producto_id'], orden['sede_id'], item['cantidad'], f"Cancelacion orden {id}"))
            
        execute("UPDATE public.ordenes SET estado = 'cancelada', actualizado_en = NOW() WHERE id = %s", (id,))
        return jsonify({"success": True, "message": "Orden cancelada", "data": None}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500
