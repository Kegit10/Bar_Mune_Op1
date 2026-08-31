import uuid
import datetime
from decimal import Decimal
from flask import Blueprint, request, jsonify
from app.db import query, query_one
from app.utils.decorators import require_auth

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


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


@dashboard_bp.route('/stats', methods=['GET'])
@require_auth
def get_dashboard_stats():
    try:
        sede_id = request.args.get('sede_id')

        # 1. Ventas de Hoy (por fecha de pago)
        sql_ventas = """
            SELECT COALESCE(SUM(p.monto_total), 0) as total_hoy,
                   COUNT(p.id) as num_ventas_hoy
            FROM public.pagos p
            JOIN public.ordenes o ON p.orden_id = o.id
            WHERE DATE(p.created_at) = CURRENT_DATE
        """
        params_v = []
        if sede_id:
            sql_ventas += " AND o.sede_id = %s"
            params_v.append(sede_id)
        row_ventas = query_one(sql_ventas, tuple(params_v))
        ventas_hoy = float(row_ventas['total_hoy']) if row_ventas else 0.0

        # 2. Órdenes Activas
        sql_ordenes = """
            SELECT COUNT(*) as ordenes_activas
            FROM public.ordenes
            WHERE estado IN ('abierta', 'en_proceso', 'lista')
        """
        params_o = []
        if sede_id:
            sql_ordenes += " AND sede_id = %s"
            params_o.append(sede_id)
        row_ord = query_one(sql_ordenes, tuple(params_o))
        ordenes_activas = int(row_ord['ordenes_activas']) if row_ord else 0

        # 3. Alertas de Stock
        sql_alertas = """
            SELECT COUNT(*) as alertas_stock
            FROM public.productos
            WHERE stock_actual <= stock_minimo AND estado != 'inactivo'
        """
        params_a = []
        if sede_id:
            sql_alertas += " AND sede_id = %s"
            params_a.append(sede_id)
        row_al = query_one(sql_alertas, tuple(params_a))
        alertas_stock = int(row_al['alertas_stock']) if row_al else 0

        # 4. Total Productos Activos
        sql_prods = """
            SELECT COUNT(*) as total_prods
            FROM public.productos
            WHERE estado = 'activo'
        """
        params_p = []
        if sede_id:
            sql_prods += " AND sede_id = %s"
            params_p.append(sede_id)
        row_p = query_one(sql_prods, tuple(params_p))
        total_prods = int(row_p['total_prods']) if row_p else 0

        # 5. Últimas 5 Ventas
        sql_ultimas = """
            SELECT p.id, p.monto_total, p.metodo_pago, p.numero_comprobante, p.created_at,
                   o.mesa, o.numero_orden, s.nombre as sede_nombre,
                   u.nombre || ' ' || COALESCE(u.apellido, '') as cajero_nombre
            FROM public.pagos p
            JOIN public.ordenes o ON p.orden_id = o.id
            LEFT JOIN public.sedes s ON o.sede_id = s.id
            LEFT JOIN public.usuarios u ON p.cajero_id = u.id
            WHERE 1=1
        """
        params_u = []
        if sede_id:
            sql_ultimas += " AND o.sede_id = %s"
            params_u.append(sede_id)
        sql_ultimas += " ORDER BY p.created_at DESC LIMIT 5"
        ultimas_ventas = query(sql_ultimas, tuple(params_u))

        data = {
            "ventas_hoy": ventas_hoy,
            "ordenes_activas": ordenes_activas,
            "alertas_stock": alertas_stock,
            "total_productos": total_prods,
            "ultimas_ventas": serialize(ultimas_ventas)
        }

        return jsonify({"success": True, "message": "Estadísticas obtenidas", "data": data}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500
