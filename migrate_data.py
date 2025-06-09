from app import db, create_app
from app.models import TOFSReport, User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Buat tabel di PostgreSQL
app = create_app()
with app.app_context():
    db.create_all()

# Koneksi ke SQLite
sqlite_engine = create_engine('sqlite:///tofs.db')
SQLiteSession = sessionmaker(bind=sqlite_engine)
sqlite_session = SQLiteSession()

# Koneksi ke PostgreSQL
postgres_engine = create_engine("postgresql+psycopg://postgres:Koplak21koplak?@localhost:5432/tofs_db")
PostgresSession = sessionmaker(bind=postgres_engine)
postgres_session = PostgresSession()

# Ambil semua data dari SQLite
reports = sqlite_session.query(TOFSReport).all()
users = sqlite_session.query(User).all()

# Pindahkan ke PostgreSQL
for r in reports:
    postgres_session.merge(r)

for u in users:
    postgres_session.merge(u)

postgres_session.commit()
print("Migrasi selesai.")
