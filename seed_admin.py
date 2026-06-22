from app import create_app
from extensions import db
from services.auth_service import crear_usuario

app = create_app()

with app.app_context():
    try:
        admin = crear_usuario(
            nombre="PERCY",
            dni="60791795",
            email="percy19marceliano@gmail.com",
            telefono="929522958",
            password_plano="933401647xd:()",
            rol="admin",
        )
        admin.correo_verificado = True
        admin.telefono_verificado = True
        db.session.commit()
        print(f"Cuenta admin creada: {admin.email}")
    except ValueError as e:
        print(f"No se pudo crear: {e}")