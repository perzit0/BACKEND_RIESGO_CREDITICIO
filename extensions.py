from flask_sqlalchemy import SQLAlchemy
 
# db se instancia aqui, vacio, y se conecta a la app real con db.init_app(app)
# dentro de app.py. Esto evita el import circular: si db se creara directo
# en app.py, los archivos de models/ no podrian importarlo sin terminar
# importando tambien app.py (que a su vez importa los models). Asi, todos
# importan extensions.py, que no depende de nadie.
db = SQLAlchemy()