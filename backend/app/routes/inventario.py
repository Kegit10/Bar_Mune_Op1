import uuid
import datetime
from decimal import Decimal
from flask import Blueprint, request, jsonify
from app.db import query, query_one, execute, execute_one
from app.utils.decorators import require_auth, require_roles

inventario_bp = Blueprint('inventario', __name__, url_prefix='/api')

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

@inventario_bp.route('/productos', methods=['GET'])
@require_auth
def get_productos():
    try:
        sede_id = request.args.get('sede_id')
        categoria_id = request.args.get('categoria_id')
        search = request.args.get('search')
        estado = request.args.get('estado')
        limit = request.args.get('limit', 100)
        
        sql = """
            SELECT p.*, c.nombre as categoria_nombre, s.nombre as sede_nombre
            FROM public.productos p
            LEFT JOIN public.categorias c ON p.categoria_id = c.id
            LEFT JOIN public.sedes s ON p.sede_id = s.id
            WHERE 1=1
        """
        params = []
        
        if sede_id:
            sql += " AND p.sede_id = %s"
            params.append(sede_id)
        if categoria_id:
            sql += " AND p.categoria_id = %s"
            params.append(categoria_id)
        if estado:
            sql += " AND p.estado = %s"
            params.append(estado)
        if search:
            sql += " AND (p.nombre ILIKE %s OR p.codigo ILIKE %s)"
            params.extend([f"%{search}%", f"%{search}%"])
            
        sql += " ORDER BY p.creado_en DESC LIMIT %s"
        params.append(int(limit))
        
        rows = query(sql, tuple(params))
        return jsonify({"success": True, "message": "Productos obtenidos", "data": serialize(rows)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@inventario_bp.route('/productos/alertas', methods=['GET'])
@require_auth
def get_productos_alertas():
    try:
        sql = """
            SELECT p.*, c.nombre as categoria_nombre, s.nombre as sede_nombre
            FROM public.productos p
            LEFT JOIN public.categorias c ON p.categoria_id = c.id
            LEFT JOIN public.sedes s ON p.sede_id = s.id
            WHERE p.stock_actual <= p.stock_minimo AND p.estado != 'inactivo'
            ORDER BY p.stock_actual ASC
        """
        rows = query(sql, ())
        return jsonify({"success": True, "message": "Alertas obtenidas", "data": serialize(rows)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@inventario_bp.route('/productos/<id>', methods=['GET'])
@require_auth
def get_producto(id):
    try:
        sql = """
            SELECT p.*, c.nombre as categoria_nombre, s.nombre as sede_nombre
            FROM public.productos p
            LEFT JOIN public.categorias c ON p.categoria_id = c.id
            LEFT JOIN public.sedes s ON p.sede_id = s.id
            WHERE p.id = %s
        """
        row = query_one(sql, (id,))
        if not row:
            return jsonify({"success": False, "message": "Producto no encontrado", "data": None}), 404
        return jsonify({"success": True, "message": "Producto obtenido", "data": serialize(row)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@inventario_bp.route('/productos', methods=['POST'])
@require_auth
@require_roles(['admin', 'cajero'])
def create_producto():
    try:
        data = request.json
        codigo = data.get('codigo')
        nombre = data.get('nombre')
        categoria_id = data.get('categoria_id')
        sede_id = data.get('sede_id')
        precio = data.get('precio')
        costo = data.get('costo', 0)
        stock_actual = data.get('stock_actual', 0)
        stock_minimo = data.get('stock_minimo', 0)
        estado = data.get('estado', 'activo')
        
        if not codigo or not nombre or not categoria_id or not sede_id or precio is None:
            return jsonify({"success": False, "message": "Faltan campos", "data": None}), 400
            
        existing = query_one("SELECT id FROM public.productos WHERE codigo = %s AND sede_id = %s", (codigo, sede_id))
        if existing:
            return jsonify({"success": False, "message": "Código ya existe en esta sede", "data": None}), 400
            
        sql = """
            INSERT INTO public.productos (codigo, nombre, categoria_id, sede_id, precio, costo, stock_actual, stock_minimo, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        row = execute_one(sql, (codigo, nombre, categoria_id, sede_id, precio, costo, stock_actual, stock_minimo, estado))
        return jsonify({"success": True, "message": "Producto creado", "data": serialize(row)}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@inventario_bp.route('/productos/<id>', methods=['PUT'])
@require_auth
@require_roles(['admin', 'cajero'])
def update_producto(id):
    try:
        data = request.json
        
        prod = query_one("SELECT id FROM public.productos WHERE id = %s", (id,))
        if not prod:
            return jsonify({"success": False, "message": "Producto no encontrado", "data": None}), 404
            
        updates = []
        params = []
        for field in ['codigo', 'nombre', 'categoria_id', 'sede_id', 'precio', 'costo', 'stock_actual', 'stock_minimo', 'estado']:
            if field in data:
                updates.append(f"{field} = %s")
                params.append(data[field])
                
        if not updates:
            return jsonify({"success": False, "message": "Sin datos", "data": None}), 400
            
        updates.append("actualizado_en = NOW()")
        sql = f"UPDATE public.productos SET {', '.join(updates)} WHERE id = %s RETURNING *"
        params.append(id)
        
        row = execute_one(sql, tuple(params))
        return jsonify({"success": True, "message": "Producto actualizado", "data": serialize(row)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@inventario_bp.route('/productos/<id>', methods=['DELETE'])
@require_auth
@require_roles(['admin'])
def delete_producto(id):
    try:
        prod = query_one("SELECT id FROM public.productos WHERE id = %s", (id,))
        if not prod:
            return jsonify({"success": False, "message": "Producto no encontrado", "data": None}), 404
            
        sql = "UPDATE public.productos SET estado = 'inactivo', actualizado_en = NOW() WHERE id = %s RETURNING *"
        row = execute_one(sql, (id,))
        return jsonify({"success": True, "message": "Producto desactivado", "data": serialize(row)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@inventario_bp.route('/categorias', methods=['GET'])
@require_auth
def get_categorias():
    try:
        sql = "SELECT * FROM public.categorias ORDER BY nombre ASC"
        rows = query(sql, ())
        return jsonify({"success": True, "message": "Categorías obtenidas", "data": serialize(rows)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500

@inventario_bp.route('/categorias', methods=['POST'])
@require_auth
@require_roles(['admin'])
def create_categoria():
    try:
        data = request.json
        nombre = data.get('nombre')
        descripcion = data.get('descripcion')
        
        if not nombre:
            return jsonify({"success": False, "message": "Nombre requerido", "data": None}), 400
            
        sql = "INSERT INTO public.categorias (nombre, descripcion) VALUES (%s, %s) RETURNING *"
        row = execute_one(sql, (nombre, descripcion))
        return jsonify({"success": True, "message": "Categoría creada", "data": serialize(row)}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500
