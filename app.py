import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from flask_cors import CORS
from extensions import db
from config import Config

from models.usuario import Usuario
from models.evaluacion import Evaluacion


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app)
    db.init_app(app)

    # CORRECCIÓN: registrar blueprints ANTES de create_all para que
    # todos los modelos estén cargados cuando se crean las tablas
    from routes.auth_routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/api/auth")

    from routes.user_routes import user_bp
    app.register_blueprint(user_bp, url_prefix="/api/user")

    from routes.admin_routes import admin_bp
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    with app.app_context():
        db.create_all()
        _seed_admin_si_no_existe()

    return app


def _seed_admin_si_no_existe():
    from services.auth_service import crear_usuario
    admin_email = os.environ.get("ADMIN_EMAIL", "percy19marceliano@gmail.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin133")
    admin_dni = os.environ.get("ADMIN_DNI", "60791795")
    admin_telefono = os.environ.get("ADMIN_TELEFONO", "929522958")

    if not Usuario.query.filter_by(email=admin_email).first():
        try:
            admin = crear_usuario(
                nombre="Administrador UNFV",
                dni=admin_dni,
                email=admin_email,
                telefono=admin_telefono,
                password_plano=admin_password,
                rol="admin",
            )
            admin.correo_verificado = True
            admin.telefono_verificado = True
            from extensions import db as _db
            _db.session.commit()
            print(f"[SEED] Admin creado: {admin_email}")
        except Exception as e:
            print(f"[SEED] Admin ya existe o error: {e}")


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
