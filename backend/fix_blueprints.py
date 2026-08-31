import os, re

# Map: filename -> (old_var, new_var)
fixes = {
    'usuarios.py':   ('bp', 'usuarios_bp'),
    'sedes.py':      ('bp', 'sedes_bp'),
    'parametros.py': ('bp', 'parametros_bp'),
    'inventario.py': ('bp', 'inventario_bp'),
    'ordenes.py':    ('bp', 'ordenes_bp'),
    'pagos.py':      ('bp', 'pagos_bp'),
    'reportes.py':   ('bp', 'reportes_bp'),
}

routes_dir = r'app\routes'
for fname, (old, new) in fixes.items():
    fpath = os.path.join(routes_dir, fname)
    if not os.path.exists(fpath):
        print(f'SKIP (not found): {fname}')
        continue
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    # Replace only if the old var is used as blueprint name
    if f'{old} = Blueprint(' in content:
        # Replace var name in definition and all @bp.route decorators
        new_content = content.replace(f'{old} = Blueprint(', f'{new} = Blueprint(')
        new_content = new_content.replace(f'@{old}.route(', f'@{new}.route(')
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Fixed: {fname}  ({old} -> {new})')
    else:
        print(f'OK (already correct or different): {fname}')

print('Done.')
