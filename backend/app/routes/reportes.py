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


def get_ventas_data(desde=None, hasta=None, sede_id=None):
    """Consulta la base de datos para obtener las ventas reales."""
    sql = """
        SELECT o.id, o.numero_orden, o.mesa, o.estado,
               o.subtotal, o.impuesto, o.total, o.created_at,
               s.nombre as sede,
               COALESCE(u.nombre || ' ' || COALESCE(u.apellido, ''), 'Sin mesero') as mesero,
               COALESCE(p.metodo_pago, 'efectivo') as metodo_pago,
               COALESCE(p.propina, 0) as propina,
               COALESCE(p.numero_comprobante, '') as numero_comprobante
        FROM public.ordenes o
        LEFT JOIN public.sedes s ON o.sede_id = s.id
        LEFT JOIN public.usuarios u ON o.mesero_id = u.id
        LEFT JOIN public.pagos p ON p.orden_id = o.id
        WHERE o.estado IN ('pagada', 'cerrada')
    """
    params = []
    if desde:
        sql += " AND DATE(o.created_at) >= %s"
        params.append(desde)
    if hasta:
        sql += " AND DATE(o.created_at) <= %s"
        params.append(hasta)
    if sede_id:
        sql += " AND o.sede_id = %s"
        params.append(sede_id)

    sql += " ORDER BY o.created_at DESC"
    rows = query(sql, tuple(params))
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


def get_inventario_data(sede_id=None, categoria_id=None):
    """Consulta la base de datos para obtener el inventario real."""
    sql = """
        SELECT p.id, p.codigo, p.nombre, p.stock_actual, p.stock_minimo,
               p.precio_venta, p.precio_costo, p.estado,
               c.nombre as categoria, s.nombre as sede,
               (p.stock_actual * p.precio_costo) as valor_inventario
        FROM public.productos p
        LEFT JOIN public.categorias c ON p.categoria_id = c.id
        LEFT JOIN public.sedes s ON p.sede_id = s.id
        WHERE p.estado != 'inactivo'
    """
    params = []
    if sede_id:
        sql += " AND p.sede_id = %s"
        params.append(sede_id)
    if categoria_id:
        sql += " AND p.categoria_id = %s"
        params.append(categoria_id)

    sql += " ORDER BY s.nombre, c.nombre, p.nombre ASC"
    rows = query(sql, tuple(params))
    serialized = serialize(rows)
    for r in serialized:
        r['costo'] = r.get('precio_costo', 0)
        r['precio'] = r.get('precio_venta', 0)
        r['stock'] = r.get('stock_actual', 0)
    return serialized


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

        data = get_ventas_data(desde, hasta, sede_id)
        total_ventas = sum(float(r.get('total') or 0) for r in data)
        total_propinas = sum(float(r.get('propina') or 0) for r in data)
        num_ordenes = len(data)
        promedio = round(total_ventas / num_ordenes, 2) if num_ordenes > 0 else 0

        summary = {
            "total_ventas": total_ventas,
            "total_propinas": total_propinas,
            "num_ordenes": num_ordenes,
            "promedio_orden": promedio
        }

        return jsonify({
            "success": True,
            "message": "Preview ventas obtenido",
            "data": data,
            "summary": summary
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

        data = get_inventario_data(sede_id, categoria_id)
        valor_total = sum(float(r.get('valor_inventario') or 0) for r in data)
        stock_total = sum(int(r.get('stock_actual') or 0) for r in data)
        num_productos = len(data)

        summary = {
            "valor_total": valor_total,
            "stock_total": stock_total,
            "total_productos": num_productos
        }

        return jsonify({
            "success": True,
            "message": "Preview inventario obtenido",
            "data": data,
            "summary": summary
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
