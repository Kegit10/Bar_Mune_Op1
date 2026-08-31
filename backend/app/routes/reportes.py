import uuid
import datetime
from decimal import Decimal
from flask import Blueprint, request, jsonify, send_file
from app.db import query, query_one, execute, execute_one
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

@reportes_bp.route('/inventario/preview', methods=['GET'])
@require_auth
def preview_inventario():
    try:
        sql = """
            SELECT p.codigo, p.nombre, p.stock_actual, p.stock_minimo, p.precio, p.costo, c.nombre as categoria, s.nombre as sede
            FROM public.productos p
            LEFT JOIN public.categorias c ON p.categoria_id = c.id
            LEFT JOIN public.sedes s ON p.sede_id = s.id
            ORDER BY s.nombre, c.nombre, p.nombre
        """
        rows = query(sql, ())
        return jsonify({"success": True, "message": "Preview inventario", "data": serialize(rows)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@reportes_bp.route('/inventario', methods=['GET'])
@require_auth
def reporte_inventario():
    try:
        formato = request.args.get('format', 'xlsx')
        
        sql = """
            SELECT p.codigo, p.nombre, p.stock_actual, p.stock_minimo, p.precio, p.costo, c.nombre as categoria, s.nombre as sede
            FROM public.productos p
            LEFT JOIN public.categorias c ON p.categoria_id = c.id
            LEFT JOIN public.sedes s ON p.sede_id = s.id
            ORDER BY s.nombre, c.nombre, p.nombre
        """
        rows = query(sql, ())
        
        data_dicts = serialize(rows)
        headers = ['codigo', 'nombre', 'stock_actual', 'stock_minimo', 'precio', 'costo', 'categoria', 'sede']
        
        if formato == 'csv':
            filepath = generate_csv_report("Reporte_Inventario", headers, data_dicts)
            mimetype = 'text/csv'
        else:
            filepath = generate_excel_report("Reporte_Inventario", headers, data_dicts)
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            
        return send_file(filepath, as_attachment=True, download_name=f"inventario.{formato}", mimetype=mimetype)
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@reportes_bp.route('/ventas/preview', methods=['GET'])
@require_auth
def preview_ventas():
    try:
        desde = request.args.get('desde')
        hasta = request.args.get('hasta')
        sede_id = request.args.get('sede_id')
        
        sql = """
            SELECT o.id, o.mesa, o.estado, o.subtotal, o.impuesto, o.total, o.creado_en as fecha, s.nombre as sede
            FROM public.ordenes o
            LEFT JOIN public.sedes s ON o.sede_id = s.id
            WHERE o.estado IN ('pagada', 'cerrada')
        """
        params = []
        if desde:
            sql += " AND DATE(o.creado_en) >= %s"
            params.append(desde)
        if hasta:
            sql += " AND DATE(o.creado_en) <= %s"
            params.append(hasta)
        if sede_id:
            sql += " AND o.sede_id = %s"
            params.append(sede_id)
            
        sql += " ORDER BY o.creado_en DESC"
        
        rows = query(sql, tuple(params))
        return jsonify({"success": True, "message": "Preview ventas", "data": serialize(rows)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@reportes_bp.route('/ventas', methods=['GET'])
@require_auth
def reporte_ventas():
    try:
        desde = request.args.get('desde')
        hasta = request.args.get('hasta')
        sede_id = request.args.get('sede_id')
        formato = request.args.get('format', 'xlsx')
        
        sql = """
            SELECT o.id, o.mesa, o.estado, o.subtotal, o.impuesto, o.total, o.creado_en as fecha, s.nombre as sede
            FROM public.ordenes o
            LEFT JOIN public.sedes s ON o.sede_id = s.id
            WHERE o.estado IN ('pagada', 'cerrada')
        """
        params = []
        if desde:
            sql += " AND DATE(o.creado_en) >= %s"
            params.append(desde)
        if hasta:
            sql += " AND DATE(o.creado_en) <= %s"
            params.append(hasta)
        if sede_id:
            sql += " AND o.sede_id = %s"
            params.append(sede_id)
            
        sql += " ORDER BY o.creado_en DESC"
        
        rows = query(sql, tuple(params))
        data_dicts = serialize(rows)
        headers = ['id', 'mesa', 'estado', 'subtotal', 'impuesto', 'total', 'fecha', 'sede']
        
        if formato == 'csv':
            filepath = generate_csv_report("Reporte_Ventas", headers, data_dicts)
            mimetype = 'text/csv'
        else:
            filepath = generate_excel_report("Reporte_Ventas", headers, data_dicts)
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            
        return send_file(filepath, as_attachment=True, download_name=f"ventas.{formato}", mimetype=mimetype)
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500
