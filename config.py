import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')

    # Gunakan PostgreSQL jika DATABASE_URL diset, fallback ke SQLite
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL") or
        f"sqlite:///{os.path.join(basedir, 'tofs.db')}"
    )
