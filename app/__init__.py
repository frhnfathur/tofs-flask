import os
import secrets
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__) 
    
    # Konfigurasi dasar
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.secret_key = secrets.token_hex(16)
    
    # Ganti ini dengan koneksi database yang kamu pakai, contoh PostgreSQL:
    app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql+psycopg://postgres:Koplak21koplak?@localhost:5432/tofs_db"
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(basedir, '..', 'uploads')

    # Inisialisasi ekstensi
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # sesuai blueprint login

    # Import model di sini agar dikenali oleh Alembic (penting untuk autogenerate)
    from app.models import User, TOFSReport

    # Registrasi blueprint
    from app.routes import bp as main_bp
    from app.auth import auth as auth_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    return app

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))
