from flask import Flask
from flask_cors import CORS
from extensions import db
from config import Config

# Se importan los modelos aqui para que SQLAlchemy los registre antes
# de que db.create_all() intente crear las tablas en la base de datos.
from models.usuario import Usuario
from models.evaluacion import Evaluacion


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app)  # permite que el frontend (app movil o web) consuma esta API
    db.init_app(app)

    with app.app_context():
        db.create_all()

    from routes.auth_routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/api/auth")

    from routes.user_routes import user_bp
    app.register_blueprint(user_bp, url_prefix="/api/user")

    from routes.admin_routes import admin_bp
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)