from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
from models import db, TOFSReport, User
from werkzeug.utils import secure_filename
from flask import jsonify 
from sqlalchemy import func, case
from sqlalchemy import and_
import os
import secrets
from flask import flash, session, redirect, url_for
from collections import Counter, defaultdict
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from flask import abort


app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'tofs.db')}"
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

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

@app.route('/')
def index():
    # Ambil parameter filter dari query string
    name = request.args.get('name', '').strip()
    division = request.args.get('division', '').strip()
    site = request.args.get('site', '').strip()
    sub_location = request.args.get('sub_location', '').strip()
    status = request.args.get('status', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

    query = TOFSReport.query
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

    reports = query.order_by(TOFSReport.date.desc()).all()

    # Data unik untuk dropdown filter (diambil dari db)
    distinct_divisions = sorted(set(r.division for r in TOFSReport.query.with_entities(TOFSReport.division).distinct()))
    distinct_sites = sorted(set(r.site for r in TOFSReport.query.with_entities(TOFSReport.site).distinct()))
    distinct_status = sorted(set(r.status for r in TOFSReport.query.with_entities(TOFSReport.status).distinct()))

    user_role = 'user'

    return render_template('index.html',
                           reports=reports,
                           distinct_divisions=distinct_divisions,
                           distinct_sites=distinct_sites,
                           distinct_status=distinct_status,
                           filters=request.args,
                           user_role=user_role)

@app.route('/add', methods=['GET', 'POST'])
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
            status=status
        )
        db.session.add(report)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('form.html')

# UPDATE data TOFS
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
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
        report.clsr = request.form['clsr_terkait']
        report.status = request.form['status']
        db.session.commit()
        flash('Data TOFS berhasil diperbarui.', 'success')
        return redirect(url_for('index'))
    return render_template('edit.html', report=report, clsr_options=CLSR_OPTIONS)


# DELETE data TOFS
@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    report = TOFSReport.query.get_or_404(id)
    db.session.delete(report)
    db.session.commit()
    flash('Data TOFS berhasil dihapus.', 'success')
    return redirect(url_for('index'))


@app.route('/dashboard', methods=['GET'])
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

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error_message="Halaman yang kamu cari tidak ditemukan."), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error_message="Terjadi kesalahan server. Silakan coba lagi nanti."), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
