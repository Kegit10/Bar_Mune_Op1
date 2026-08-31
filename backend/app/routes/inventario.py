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


def format_producto(p):
    """Agrega aliases compatibles para frontend (precio, costo)."""
    if not p:
        return None
    p_dict = serialize(p)
    p_dict['precio'] = p_dict.get('precio_venta', 0)
    p_dict['costo'] = p_dict.get('precio_costo', 0)
    p_dict['stock'] = p_dict.get('stock_actual', 0)
    return p_dict


# ============================================================
# CATEGORIAS
# ============================================================
@inventario_bp.route('/categorias', methods=['GET'])
@require_auth
def get_categorias():
    try:
        sql = "SELECT DISTINCT ON (nombre) id, nombre, descripcion, color, activa, created_at FROM public.categorias WHERE activa = true ORDER BY nombre ASC, created_at ASC"
        rows = query(sql, ())
        return jsonify({"success": True, "message": "Categorías obtenidas", "data": serialize(rows)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@inventario_bp.route('/categorias', methods=['POST'])
@require_auth
@require_roles('admin')
def create_categoria():
    try:
        data = request.get_json() or {}
        nombre = (data.get('nombre') or '').strip()
        descripcion = (data.get('descripcion') or '').strip()
        color = data.get('color', '#6366F1')

        if not nombre:
            return jsonify({"success": False, "message": "El nombre de la categoría es requerido", "data": None}), 400

        sql = "INSERT INTO public.categorias (nombre, descripcion, color) VALUES (%s, %s, %s) RETURNING *"
        row = execute_one(sql, (nombre, descripcion, color))
        return jsonify({"success": True, "message": "Categoría creada", "data": serialize(row)}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


# ============================================================
# ALERTAS DE STOCK (Registrado antes de /productos/<id>)
# ============================================================
@inventario_bp.route('/productos/alertas', methods=['GET'])
@require_auth
def get_productos_alertas():
    try:
        sql = """
            SELECT p.id, p.codigo, p.nombre, p.descripcion, p.precio_costo, p.precio_venta,
                   p.stock_actual, p.stock_minimo, p.categoria_id, p.sede_id, p.estado, p.created_at,
                   c.nombre as categoria_nombre, s.nombre as sede_nombre,
                   (p.stock_minimo - p.stock_actual) as deficit
            FROM public.productos p
            LEFT JOIN public.categorias c ON p.categoria_id = c.id
            LEFT JOIN public.sedes s ON p.sede_id = s.id
            WHERE p.stock_actual <= p.stock_minimo AND p.estado != 'inactivo'
            ORDER BY (p.stock_actual = 0) DESC, p.stock_actual ASC
        """
        rows = query(sql, ())
        formatted = [format_producto(r) for r in rows]
        return jsonify({"success": True, "message": "Alertas de stock obtenidas", "data": formatted}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


# ============================================================
# PRODUCTOS CRUD
# ============================================================
@inventario_bp.route('/productos', methods=['GET'])
@require_auth
def get_productos():
    try:
        sede_id = request.args.get('sede_id')
        categoria_id = request.args.get('categoria_id')
        search = request.args.get('search')
        estado = request.args.get('estado')
        limit = request.args.get('limit', 500)

        sql = """
            SELECT p.id, p.codigo, p.nombre, p.descripcion, p.precio_costo, p.precio_venta,
                   p.stock_actual, p.stock_minimo, p.categoria_id, p.sede_id, p.estado, p.imagen_url, p.created_at,
                   c.nombre as categoria_nombre, s.nombre as sede_nombre
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

        sql += " ORDER BY p.nombre ASC LIMIT %s"
        params.append(int(limit))

        rows = query(sql, tuple(params))
        formatted = [format_producto(r) for r in rows]
        return jsonify({"success": True, "message": "Productos obtenidos", "data": formatted}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@inventario_bp.route('/productos/<id>', methods=['GET'])
@require_auth
def get_producto(id):
    try:
        sql = """
            SELECT p.id, p.codigo, p.nombre, p.descripcion, p.precio_costo, p.precio_venta,
                   p.stock_actual, p.stock_minimo, p.categoria_id, p.sede_id, p.estado, p.imagen_url, p.created_at,
                   c.nombre as categoria_nombre, s.nombre as sede_nombre
            FROM public.productos p
            LEFT JOIN public.categorias c ON p.categoria_id = c.id
            LEFT JOIN public.sedes s ON p.sede_id = s.id
            WHERE p.id = %s
        """
        row = query_one(sql, (id,))
        if not row:
            return jsonify({"success": False, "message": "Producto no encontrado", "data": None}), 404
        return jsonify({"success": True, "message": "Producto obtenido", "data": format_producto(row)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@inventario_bp.route('/productos', methods=['POST'])
@require_auth
@require_roles('admin', 'cajero')
def create_producto():
    try:
        data = request.get_json() or {}
        codigo = (data.get('codigo') or '').strip().upper()
        nombre = (data.get('nombre') or '').strip()
        descripcion = data.get('descripcion', '')
        categoria_id = data.get('categoria_id') or None
        sede_id = data.get('sede_id') or None
        precio_venta = float(data.get('precio_venta') or data.get('precio') or 0)
        precio_costo = float(data.get('precio_costo') or data.get('costo') or 0)
        stock_actual = int(data.get('stock_actual') or data.get('stock') or 0)
        stock_minimo = int(data.get('stock_minimo') or 5)
        estado = data.get('estado', 'activo')

        if not codigo or not nombre or not sede_id:
            return jsonify({"success": False, "message": "Código, nombre y sede son requeridos", "data": None}), 400

        # Verificar unicidad de código por sede
        existing = query_one("SELECT id FROM public.productos WHERE codigo = %s AND sede_id = %s", (codigo, sede_id))
        if existing:
            return jsonify({"success": False, "message": f"El código '{codigo}' ya existe en esta sede", "data": None}), 400

        sql = """
            INSERT INTO public.productos (codigo, nombre, descripcion, precio_costo, precio_venta, stock_actual, stock_minimo, categoria_id, sede_id, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        row = execute_one(sql, (codigo, nombre, descripcion, precio_costo, precio_venta, stock_actual, stock_minimo, categoria_id, sede_id, estado))
        return jsonify({"success": True, "message": "Producto creado exitosamente", "data": format_producto(row)}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@inventario_bp.route('/productos/<id>', methods=['PUT'])
@require_auth
@require_roles('admin', 'cajero')
def update_producto(id):
    try:
        data = request.get_json() or {}
        prod = query_one("SELECT id FROM public.productos WHERE id = %s", (id,))
        if not prod:
            return jsonify({"success": False, "message": "Producto no encontrado", "data": None}), 404

        updates = []
        params = []

        if 'codigo' in data:
            updates.append("codigo = %s")
            params.append(data['codigo'].strip().upper())
        if 'nombre' in data:
            updates.append("nombre = %s")
            params.append(data['nombre'].strip())
        if 'descripcion' in data:
            updates.append("descripcion = %s")
            params.append(data['descripcion'])
        if 'categoria_id' in data:
            updates.append("categoria_id = %s")
            params.append(data['categoria_id'] if data['categoria_id'] else None)
        if 'sede_id' in data:
            updates.append("sede_id = %s")
            params.append(data['sede_id'] if data['sede_id'] else None)
        if 'precio_venta' in data or 'precio' in data:
            updates.append("precio_venta = %s")
            params.append(float(data.get('precio_venta', data.get('precio', 0))))
        if 'precio_costo' in data or 'costo' in data:
            updates.append("precio_costo = %s")
            params.append(float(data.get('precio_costo', data.get('costo', 0))))
        if 'stock_actual' in data or 'stock' in data:
            updates.append("stock_actual = %s")
            params.append(int(data.get('stock_actual', data.get('stock', 0))))
        if 'stock_minimo' in data:
            updates.append("stock_minimo = %s")
            params.append(int(data['stock_minimo']))
        if 'estado' in data:
            updates.append("estado = %s")
            params.append(data['estado'])

        if not updates:
            return jsonify({"success": False, "message": "Sin datos para actualizar", "data": None}), 400

        updates.append("updated_at = NOW()")
        sql = f"UPDATE public.productos SET {', '.join(updates)} WHERE id = %s RETURNING *"
        params.append(id)

        row = execute_one(sql, tuple(params))
        return jsonify({"success": True, "message": "Producto actualizado exitosamente", "data": format_producto(row)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500


@inventario_bp.route('/productos/<id>', methods=['DELETE'])
@require_auth
@require_roles('admin')
def delete_producto(id):
    try:
        prod = query_one("SELECT id FROM public.productos WHERE id = %s", (id,))
        if not prod:
            return jsonify({"success": False, "message": "Producto no encontrado", "data": None}), 404

        sql = "UPDATE public.productos SET estado = 'inactivo', updated_at = NOW() WHERE id = %s RETURNING id"
        row = execute_one(sql, (id,))
        return jsonify({"success": True, "message": "Producto desactivado exitosamente", "data": serialize(row)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "data": None}), 500
