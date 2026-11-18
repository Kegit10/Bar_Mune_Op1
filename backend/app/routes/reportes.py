import uuid
import datetime
from decimal import Decimal
from flask import Blueprint, request, jsonify, send_file
from app.db import query, query_one
from app.utils.decorators import require_auth, require_roles
from app.utils.reports import generate_excel_report, generate_csv_report

reportes_bp = Blueprint('reportes', __name__, url_prefix='/api/reportes')


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


def get_ventas_data(desde=None, hasta=None, sede_id=None, limit=None, offset=None):
    """Consulta la base de datos para obtener las ventas reales."""
    where_sql = " WHERE o.estado IN ('pagada', 'cerrada')"
    params = []
    if desde:
        where_sql += " AND DATE(o.created_at) >= %s"
        params.append(desde)
    if hasta:
        where_sql += " AND DATE(o.created_at) <= %s"
        params.append(hasta)
    if sede_id:
        where_sql += " AND o.sede_id = %s"
        params.append(sede_id)

    sql = f"""
        SELECT o.id, o.numero_orden, o.mesa, o.estado,
               o.subtotal, o.impuesto, o.total, o.created_at,
               s.nombre as sede, s.direccion as sede_direccion, s.ciudad as sede_ciudad, s.telefono as sede_telefono,
               COALESCE(p.cliente_nombre, o.cliente_nombre, 'Consumidor Final') as cliente_nombre,
               COALESCE(p.cliente_documento, o.cliente_documento, '222222222222') as cliente_documento,
               COALESCE(u.nombre || ' ' || COALESCE(u.apellido, ''), 'Sin mesero') as mesero,
               COALESCE(p.metodo_pago, 'efectivo') as metodo_pago,
               COALESCE(p.propina, 0) as propina,
               COALESCE(p.numero_comprobante, '') as numero_comprobante
        FROM public.ordenes o
        LEFT JOIN public.sedes s ON o.sede_id = s.id
        LEFT JOIN public.usuarios u ON o.mesero_id = u.id
        LEFT JOIN public.pagos p ON p.orden_id = o.id
        {where_sql}
        ORDER BY o.created_at DESC
    """
    query_params = list(params)
    if limit is not None and offset is not None:
        sql += " LIMIT %s OFFSET %s"
        query_params.extend([int(limit), int(offset)])

    rows = query(sql, tuple(query_params))
    serialized = serialize(rows)

    # Formatear fecha legible para frontend y reportes
    for r in serialized:
        created = r.get('created_at', '')
        if created and 'T' in str(created):
            parts = str(created).split('T')
            time_part = parts[1][:5] if len(parts) > 1 else ''
            r['fecha'] = f"{parts[0]} {time_part}"
        else:
            r['fecha'] = str(created)[:16]
    return serialized


def get_ventas_summary(desde=None, hasta=None, sede_id=None):
    """Obtiene totales y conteo de ventas directamente en SQL."""
    where_sql = " WHERE o.estado IN ('pagada', 'cerrada')"
    params = []
    if desde:
        where_sql += " AND DATE(o.created_at) >= %s"
        params.append(desde)
    if hasta:
        where_sql += " AND DATE(o.created_at) <= %s"
        params.append(hasta)
    if sede_id:
        where_sql += " AND o.sede_id = %s"
        params.append(sede_id)

    sql = f"""
        SELECT COUNT(*) AS num_ordenes,
               COALESCE(SUM(o.total), 0) AS total_ventas,
               COALESCE(SUM(p.propina), 0) AS total_propinas
        FROM public.ordenes o
        LEFT JOIN public.pagos p ON p.orden_id = o.id
        {where_sql}
    """
    row = query_one(sql, tuple(params)) or {}
    num_ordenes = int(row.get('num_ordenes') or 0)
    total_ventas = float(row.get('total_ventas') or 0)
    total_propinas = float(row.get('total_propinas') or 0)
    promedio = round(total_ventas / num_ordenes, 2) if num_ordenes > 0 else 0
    return {
        "total_ventas": total_ventas,
        "total_propinas": total_propinas,
        "num_ordenes": num_ordenes,
        "promedio_orden": promedio
    }


def get_inventario_data(sede_id=None, categoria_id=None, limit=None, offset=None):
    """Consulta la base de datos para obtener el inventario real."""
    where_sql = " WHERE p.estado != 'inactivo'"
    params = []
    if sede_id:
        where_sql += " AND p.sede_id = %s"
        params.append(sede_id)
    if categoria_id:
        where_sql += " AND p.categoria_id = %s"
        params.append(categoria_id)

    sql = f"""
        SELECT p.id, p.codigo, p.nombre, p.stock_actual, p.stock_minimo,
               p.precio_venta, p.precio_costo, p.estado,
               c.nombre as categoria, s.nombre as sede,
               (p.stock_actual * p.precio_costo) as valor_inventario
        FROM public.productos p
        LEFT JOIN public.categorias c ON p.categoria_id = c.id
        LEFT JOIN public.sedes s ON p.sede_id = s.id
        {where_sql}
        ORDER BY s.nombre, c.nombre, p.nombre ASC
    """
    query_params = list(params)
    if limit is not None and offset is not None:
        sql += " LIMIT %s OFFSET %s"
        query_params.extend([int(limit), int(offset)])

    rows = query(sql, tuple(query_params))
    serialized = serialize(rows)
    for r in serialized:
        r['costo'] = r.get('precio_costo', 0)
        r['precio'] = r.get('precio_venta', 0)
        r['stock'] = r.get('stock_actual', 0)
    return serialized


def get_inventario_summary(sede_id=None, categoria_id=None):
    """Obtiene resumen de inventario directamente en SQL."""
    where_sql = " WHERE p.estado != 'inactivo'"
    params = []
    if sede_id:
        where_sql += " AND p.sede_id = %s"
        params.append(sede_id)
    if categoria_id:
        where_sql += " AND p.categoria_id = %s"
        params.append(categoria_id)

    sql = f"""
        SELECT COUNT(*) AS total_productos,
               COALESCE(SUM(p.stock_actual), 0) AS stock_total,
               COALESCE(SUM(p.stock_actual * p.precio_costo), 0) AS valor_total
        FROM public.productos p
        {where_sql}
    """
    row = query_one(sql, tuple(params)) or {}
    return {
        "valor_total": float(row.get('valor_total') or 0),
        "stock_total": int(row.get('stock_total') or 0),
        "total_productos": int(row.get('total_productos') or 0)
    }


# ============================================================
# VENTAS
# ============================================================
@reportes_bp.route('/ventas/preview', methods=['GET'])
@require_auth
def preview_ventas():
    try:
        desde = request.args.get('desde')
        hasta = request.args.get('hasta')
        sede_id = request.args.get('sede_id')
        page_param = request.args.get('page', '1')
        limit_param = request.args.get('limit', '10')

        page = max(1, int(page_param)) if str(page_param).isdigit() else 1
        limit = max(1, int(limit_param)) if str(limit_param).isdigit() else 10
        offset = (page - 1) * limit

        summary = get_ventas_summary(desde, hasta, sede_id)
        total = summary["num_ordenes"]
        total_pages = max(1, (total + limit - 1) // limit)
        data = get_ventas_data(desde, hasta, sede_id, limit=limit, offset=offset)

        return jsonify({
            "success": True,
            "message": "Preview ventas obtenido",
            "data": data,
            "summary": summary,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages
            }
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@reportes_bp.route('/ventas', methods=['GET'])
@require_auth
def reporte_ventas():
    try:
        desde = request.args.get('desde')
        hasta = request.args.get('hasta')
        sede_id = request.args.get('sede_id')
        formato = (request.args.get('format') or 'xlsx').lower()

        data = get_ventas_data(desde, hasta, sede_id)
        columns = [
            ("Fecha", "fecha"),
            ("N° Orden", "numero_orden"),
            ("Mesa", "mesa"),
            ("Sede", "sede"),
            ("Mesero", "mesero"),
            ("Subtotal ($)", "subtotal"),
            ("Impuesto ($)", "impuesto"),
            ("Propina ($)", "propina"),
            ("Total ($)", "total"),
            ("Método Pago", "metodo_pago"),
            ("N° Comprobante", "numero_comprobante")
        ]

        if formato == 'csv':
            stream = generate_csv_report("Reporte_Ventas", columns, data)
            mimetype = 'text/csv; charset=utf-8'
            filename = f"reporte_ventas_{datetime.date.today().isoformat()}.csv"
        else:
            stream = generate_excel_report("Ventas", columns, data)
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            filename = f"reporte_ventas_{datetime.date.today().isoformat()}.xlsx"

        return send_file(stream, as_attachment=True, download_name=filename, mimetype=mimetype)
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


# ============================================================
# INVENTARIO
# ============================================================
@reportes_bp.route('/inventario/preview', methods=['GET'])
@require_auth
def preview_inventario():
    try:
        sede_id = request.args.get('sede_id')
        categoria_id = request.args.get('categoria_id')
        page_param = request.args.get('page', '1')
        limit_param = request.args.get('limit', '10')

        page = max(1, int(page_param)) if str(page_param).isdigit() else 1
        limit = max(1, int(limit_param)) if str(limit_param).isdigit() else 10
        offset = (page - 1) * limit

        summary = get_inventario_summary(sede_id, categoria_id)
        total = summary["total_productos"]
        total_pages = max(1, (total + limit - 1) // limit)
        data = get_inventario_data(sede_id, categoria_id, limit=limit, offset=offset)

        return jsonify({
            "success": True,
            "message": "Preview inventario obtenido",
            "data": data,
            "summary": summary,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages
            }
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@reportes_bp.route('/inventario', methods=['GET'])
@require_auth
def reporte_inventario():
    try:
        sede_id = request.args.get('sede_id')
        categoria_id = request.args.get('categoria_id')
        formato = (request.args.get('format') or 'xlsx').lower()

        data = get_inventario_data(sede_id, categoria_id)
        columns = [
            ("Código", "codigo"),
            ("Producto", "nombre"),
            ("Categoría", "categoria"),
            ("Sede", "sede"),
            ("Costo Unitario ($)", "precio_costo"),
            ("Precio Venta ($)", "precio_venta"),
            ("Stock Actual", "stock_actual"),
            ("Stock Mínimo", "stock_minimo"),
            ("Valor Total ($)", "valor_inventario"),
            ("Estado", "estado")
        ]

        if formato == 'csv':
            stream = generate_csv_report("Reporte_Inventario", columns, data)
            mimetype = 'text/csv; charset=utf-8'
            filename = f"reporte_inventario_{datetime.date.today().isoformat()}.csv"
        else:
            stream = generate_excel_report("Inventario", columns, data)
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            filename = f"reporte_inventario_{datetime.date.today().isoformat()}.xlsx"

        return send_file(stream, as_attachment=True, download_name=filename, mimetype=mimetype)
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500
