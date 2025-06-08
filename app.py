from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
from models import db, TOFSReport, User
from werkzeug.utils import secure_filename
from flask import send_file
from sqlalchemy import func, case
from sqlalchemy import and_
import os
import secrets
from flask import flash, session, redirect, url_for
from collections import Counter, defaultdict
from math import ceil
from sqlalchemy import or_
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from functools import wraps
import pandas as pd
from io import BytesIO

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'tofs.db')}"
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

CLSR_OPTIONS = [
    "1. Tools & Equipment",
    "2. Line of Fire",
    "3. Hot Work",
    "4. Confined Space",
    "5. Powered System",
    "6. Lifting Operation",
    "7. Working at Height",
    "8. Ground-Disturbance Work",
    "9. Water-Based Work Activities",
    "10. Land Transportation"
]

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.role not in roles:
                flash('Anda tidak memiliki akses ke halaman ini.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/', methods=['GET'])
@login_required
def index():
    # Ambil parameter filter dari query string
    name = request.args.get('name', '').strip()
    division = request.args.get('division', '').strip()
    site = request.args.get('site', '').strip()
    sub_location = request.args.get('sub_location', '').strip()
    status = request.args.get('status', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '').strip()
    per_page = 10  # jumlah data per halaman

    query = TOFSReport.query.order_by(TOFSReport.date.desc())

    if search_query:
        query = query.filter(
            TOFSReport.name.ilike(f'%{search_query}%') |
            TOFSReport.division.ilike(f'%{search_query}%') |
            TOFSReport.site.ilike(f'%{search_query}%') |
            TOFSReport.sub_location.ilike(f'%{search_query}%') |
            TOFSReport.issue_description.ilike(f'%{search_query}%') |
            TOFSReport.follow_up.ilike(f'%{search_query}%') |
            TOFSReport.clsr_terkait.ilike(f'%{search_query}%') |
            TOFSReport.status.ilike(f'%{search_query}%')
        )
    else:
        reports = TOFSReport.query.order_by(TOFSReport.date.desc()).all()
    
    filters = []

    if name:
        filters.append(TOFSReport.name.ilike(f'%{name}%'))
    if division:
        filters.append(TOFSReport.division == division)
    if site:
        filters.append(TOFSReport.site == site)
    if sub_location:
        filters.append(TOFSReport.sub_location.ilike(f'%{sub_location}%'))
    if status:
        filters.append(TOFSReport.status == status)
    if date_from:
        try:
            df = datetime.strptime(date_from, '%Y-%m-%d')
            filters.append(TOFSReport.date >= df)
        except:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, '%Y-%m-%d')
            filters.append(TOFSReport.date <= dt)
        except:
            pass

    if filters:
        query = query.filter(and_(*filters))

    
    reports = query.paginate(page=page, per_page=10)
    
    # Data unik untuk dropdown filter (diambil dari db)
    distinct_divisions = sorted(set(r.division for r in TOFSReport.query.with_entities(TOFSReport.division).distinct()))
    distinct_sites = sorted(set(r.site for r in TOFSReport.query.with_entities(TOFSReport.site).distinct()))
    distinct_status = sorted(set(r.status for r in TOFSReport.query.with_entities(TOFSReport.status).distinct()))

    return render_template('index.html',
                           reports=reports,
                           distinct_divisions=distinct_divisions,
                           distinct_sites=distinct_sites,
                           distinct_status=distinct_status,
                           filters=request.args
                           )

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        name = request.form['name']
        division = request.form['division']
        site = request.form['site']
        sub_location = request.form['sub_location']
        date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        issue_description = request.form['issue_description']
        follow_up = request.form['follow_up']
        clsr_terkait = request.form['clsr_terkait']
        status = request.form['status']
        
        month = date.strftime('%m')
        year = date.strftime('%y')
        count = TOFSReport.query.filter_by(site=site).count() + 1
        card_number = f'TOFS/{site}/{month}/{year}/{count:04d}'
        
        report = TOFSReport(
            card_number=card_number,
            name=name,
            division=division,
            site=site,
            sub_location=sub_location,
            date=date,
            issue_description=issue_description,
            follow_up=follow_up,
            clsr_terkait=clsr_terkait,
            status=status,
            user_id=current_user.id
        )
        db.session.add(report)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('form.html')

# UPDATE data TOFS
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'super admin')
def edit(id):
    report = TOFSReport.query.get_or_404(id)
    if request.method == 'POST':
        report.name = request.form['name']
        report.division = request.form['division']
        report.site = request.form['site']
        report.sub_location = request.form['sub_location']
        report.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        report.issue_description = request.form['issue_description']
        report.follow_up = request.form['follow_up']
        report.clsr_terkait = request.form['clsr_terkait']
        report.status = request.form['status']
        db.session.commit()
        flash('Data TOFS berhasil diperbarui.', 'success')
        return redirect(url_for('index'))
    return render_template('edit.html', report=report, clsr_options=CLSR_OPTIONS)


# DELETE data TOFS
@app.route('/delete/<int:id>', methods=['POST'])
@login_required
@role_required('admin', 'super admin')
def delete(id):
    report = TOFSReport.query.get_or_404(id)
    db.session.delete(report)
    db.session.commit()
    flash('Data TOFS berhasil dihapus.', 'success')
    return redirect(url_for('index'))


@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    filter_site = request.args.get('site', type=str)
    filter_month = request.args.get('month', type=int)
    filter_year = request.args.get('year', type=int)
    filter_division = request.args.get('division', type=str)
    filter_status = request.args.get('status', type=str)

    query = TOFSReport.query

    if filter_site and filter_site != 'All':
        query = query.filter_by(site=filter_site)
    if filter_division and filter_division != 'All':
        query = query.filter_by(division=filter_division)
    if filter_status and filter_status != 'All':
        query = query.filter_by(status=filter_status)
    if filter_year:
        query = query.filter(db.extract('year', TOFSReport.date) == filter_year)
    if filter_month:
        query = query.filter(db.extract('month', TOFSReport.date) == filter_month)

    total_tofs = query.count()

    reports = query.all()

    # === CHART 1: Jumlah kartu TOFS per Site ===
    counts_by_site = Counter(r.site for r in reports)

    # === CHART 2: Status Open / Closed ===
    counts_status = Counter(r.status for r in reports)

    # === CHART 3: Jumlah Pengisi TOFS ===
    counts_by_name = Counter(r.name for r in reports)

    # === CHART 4: Jumlah TOFS per bulan dalam periode tertentu ===
    period = request.args.get('period', '1_year')
    today = date.today()

    if period == '6_months':
        start_date = today - timedelta(days=180)
    elif period == 'year_to_date':
        start_date = date(today.year, 1, 1)
    elif period == '3_years':
        start_date = date(today.year - 3, today.month, today.day)
    else:
        start_date = today - timedelta(days=365)

    reports_period = [r for r in reports if r.date >= start_date]

    counts_by_month = defaultdict(int)
    for r in reports_period:
        key = r.date.strftime('%Y-%m')
        counts_by_month[key] += 1

    months_sorted = sorted(counts_by_month.keys())
    counts_sorted = [counts_by_month[m] for m in months_sorted]

    # === CHART 5: CLSR Terkait ===
    clsr_raw = [r.clsr_terkait if r.clsr_terkait else 'Unknown' for r in reports]
    clsr_counter = Counter(clsr_raw)
    clsr_sorted = sorted(clsr_counter.items(), key=lambda x: x[1], reverse=True)

    clsr_labels = [item[0] for item in clsr_sorted]
    clsr_values = [item[1] for item in clsr_sorted]

    # === Filter dropdowns ===
    sites = ['All'] + sorted(set(r.site for r in TOFSReport.query.with_entities(TOFSReport.site).distinct()))
    divisions = ['All'] + sorted(set(r.division for r in TOFSReport.query.with_entities(TOFSReport.division).distinct()))
    statuses = ['All', 'Open', 'Closed']
    months = ['All'] + [i for i in range(1, 13)]
    years = ['All'] + sorted(set(r.date.year for r in TOFSReport.query.with_entities(TOFSReport.date).distinct()), reverse=True)

    return render_template('dashboard.html',
        total_tofs=total_tofs,
        counts_by_site=counts_by_site,
        counts_status=counts_status,
        counts_by_name=counts_by_name,
        months_sorted=months_sorted,
        counts_sorted=counts_sorted,
        clsr_labels=clsr_labels,
        clsr_values=clsr_values,
        sites=sites,
        divisions=divisions,
        statuses=statuses,
        months=months,
        years=years,
        filter_site=filter_site or 'All',
        filter_month=filter_month or 'All',
        filter_year=filter_year or 'All',
        filter_division=filter_division or 'All',
        filter_status=filter_status or 'All',
        selected_period=period
    )

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        work_location = request.form['work_location']

        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username atau email sudah digunakan.', 'danger')
            return redirect(url_for('register'))

        user = User(
            full_name=full_name,
            username=username,
            email=email,
            work_location=work_location,
            role='pengguna'
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registrasi berhasil. Silakan login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login gagal. Cek username/password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('login'))

#Usring#
@app.route('/users')
@login_required
def users():
    if current_user.role != 'super admin':
        flash("Akses ditolak. Hanya Super Admin yang dapat mengakses halaman ini.", "danger")
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '')

    query = User.query
    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) |
            (User.full_name.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%')) |
            (User.work_location.ilike(f'%{search}%'))
        )
    users = query.order_by(User.full_name).paginate(page=page, per_page=10)

    return render_template('users.html', users=users, search=search)

@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.role != 'super admin':
        flash("Akses ditolak.", "danger")
        return redirect(url_for('users'))

    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        user.full_name = request.form['full_name']
        user.username = request.form['username']
        user.email = request.form['email']
        user.role = request.form['role']
        user.work_location = request.form['work_location']

        password = request.form.get('password')
        if password:
            user.set_password(password)

        try:
            db.session.commit()
            flash('Data user berhasil diperbarui.', 'success')
            return redirect(url_for('users'))
        except Exception as e:
            db.session.rollback()
            flash('Terjadi kesalahan saat menyimpan data.', 'danger')

    return render_template('edit_user.html', user=user)

@app.route('/users/add', methods=['GET', 'POST'])
@login_required
def add_user():
    if current_user.role != 'super admin':
        flash("Akses ditolak. Hanya Super Admin yang dapat menambah user.", "danger")
        return redirect(url_for('users'))

    if request.method == 'POST':
        full_name = request.form['full_name']
        username = request.form['username']
        email = request.form['email']
        role = request.form['role']
        work_location = request.form.get('work_location', '')
        password = request.form['password']

        if not password:
            flash("Password harus diisi.", "danger")
            return redirect(url_for('add_user'))

        # Cek apakah username sudah ada
        if User.query.filter_by(username=username).first():
            flash("Username sudah digunakan, silakan pilih yang lain.", "danger")
            return redirect(url_for('add_user'))

        # Buat user baru
        new_user = User(
            full_name=full_name,
            username=username,
            email=email,
            role=role,
            work_location=work_location,
            password_hash=generate_password_hash(password)
        )
        try:
            db.session.add(new_user)
            db.session.commit()
            flash("User berhasil ditambahkan.", "success")
            return redirect(url_for('users'))
        except Exception as e:
            db.session.rollback()
            flash("Terjadi kesalahan saat menambahkan user.", "danger")

    return render_template('add_user.html')

@app.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'super admin':
        flash("Akses ditolak.", "danger")
        return redirect(url_for('users'))

    user = User.query.get_or_404(user_id)

    # Supaya super admin tidak bisa menghapus dirinya sendiri
    if user.id == current_user.id:
        flash("Anda tidak dapat menghapus akun Anda sendiri.", "warning")
        return redirect(url_for('users'))

    try:
        db.session.delete(user)
        db.session.commit()
        flash("User berhasil dihapus.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Terjadi kesalahan saat menghapus user.", "danger")

    return redirect(url_for('users'))



@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error_message="Halaman yang kamu cari tidak ditemukan."), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error_message="Terjadi kesalahan server. Silakan coba lagi nanti."), 500

@app.route('/download_excel')
@login_required
def download_excel():
    # Ambil filter dari query string
    name = request.args.get('name', '')
    division = request.args.get('division', '')
    site = request.args.get('site', '')
    sub_location = request.args.get('sub_location', '')
    status = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    q = request.args.get('q', '')

    # Query dengan filter yang sama seperti di halaman utama
    query = TOFSReport.query

    if name:
        query = query.filter(TOFSReport.name.ilike(f'%{name}%'))
    if division:
        query = query.filter_by(division=division)
    if site:
        query = query.filter_by(site=site)
    if sub_location:
        query = query.filter(TOFSReport.sub_location.ilike(f'%{sub_location}%'))
    if status:
        query = query.filter_by(status=status)
    if date_from:
        query = query.filter(TOFSReport.date >= date_from)
    if date_to:
        query = query.filter(TOFSReport.date <= date_to)
    if q:
        search = f"%{q}%"
        query = query.filter(
            TOFSReport.card_number.ilike(search) |
            TOFSReport.name.ilike(search) |
            TOFSReport.issue_description.ilike(search) |
            TOFSReport.follow_up.ilike(search)
        )

    reports = query.order_by(TOFSReport.date.desc()).all()

    # Konversi ke DataFrame
    data = [{
        "Nomor Kartu": r.card_number,
        "Nama": r.name,
        "Divisi": r.division,
        "Site": r.site,
        "Sub Lokasi": r.sub_location,
        "Tanggal": r.date.strftime('%d/%m/%Y'),
        "Deskripsi Isu": r.issue_description,
        "Tindak Lanjut": r.follow_up,
        "CLSR Terkait": r.clsr_terkait,
        "Status": r.status,
    } for r in reports]

    df = pd.DataFrame(data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Data TOFS')
        workbook = writer.book
        worksheet = writer.sheets['Data TOFS']
        for idx, col in enumerate(df.columns):
            column_len = df[col].astype(str).map(len).max()
            worksheet.set_column(idx, idx, column_len + 5)

    output.seek(0)
    return send_file(output, download_name='data_tofs.xlsx', as_attachment=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
