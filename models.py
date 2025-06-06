from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class TOFSReport(db.Model):
    __tablename__ = 'tofs_report'
    id = db.Column(db.Integer, primary_key=True)
    card_number = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    division = db.Column(db.String(100), nullable=False)
    site = db.Column(db.String(100), nullable=False)
    sub_location = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    issue_description = db.Column(db.Text, nullable=False)
    follow_up = db.Column(db.Text)
    clsr_terkait = db.Column(db.String(100)) 
    status = db.Column(db.String(20), nullable=False, default='Open')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')  # 'admin' atau 'user'

