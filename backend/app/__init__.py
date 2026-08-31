from flask import Flask
from flask_cors import CORS
from app.config import Config
from app.extensions import jwt

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(app)
    jwt.init_app(app)

    from app.routes.auth import auth_bp
    from app.routes.usuarios import usuarios_bp
    from app.routes.sedes import sedes_bp
    from app.routes.parametros import parametros_bp
    from app.routes.inventario import inventario_bp
    from app.routes.ordenes import ordenes_bp
    from app.routes.pagos import pagos_bp
    from app.routes.reportes import reportes_bp
    from app.routes.dashboard import dashboard_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(usuarios_bp, url_prefix='/api/usuarios')
    app.register_blueprint(sedes_bp, url_prefix='/api/sedes')
    app.register_blueprint(parametros_bp, url_prefix='/api/parametros')
    app.register_blueprint(inventario_bp, url_prefix='/api')
    app.register_blueprint(ordenes_bp, url_prefix='/api/ordenes')
    app.register_blueprint(pagos_bp, url_prefix='/api/pagos')
    app.register_blueprint(reportes_bp, url_prefix='/api/reportes')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')

    @app.route('/health', methods=['GET'])
    def health_check():
        return {"success": True, "message": "API is running", "data": None}, 200

    return app
