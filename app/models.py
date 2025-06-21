from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db

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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    perilaku_wajib = db.Column(db.String(255), nullable=True)
    site_supervisor = db.Column(db.String(100), nullable=True)
    site_superintendent = db.Column(db.String(100), nullable=True)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='pengguna')  # super admin, admin, pengguna
    work_location = db.Column(db.String(100), nullable=True)
    


    # Relationship ke laporan TOFS
    reports = db.relationship('TOFSReport', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def tofs_count(self):
        return len(self.reports)



