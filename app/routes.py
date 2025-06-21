from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, session
from flask_login import login_user, login_required, logout_user, current_user
from app.models import db, TOFSReport, User
from datetime import datetime, date, timedelta
from sqlalchemy import and_
from collections import Counter, defaultdict
from io import BytesIO
import pandas as pd
import os
import secrets
from functools import wraps
from calendar import month_name

bp = Blueprint('main', __name__)

PERILAKU_WAJIB_OPTIONS = [
    "1. Saya menerapkan HSSE Golden Rules (Patuh-Intervensi-Peduli)",
    "2. Saya kompeten dan berwenang untuk melaksanakan pekerjaan",
    "3. Saya dalam kondisi sehat untuk bekerja (Fit to Work berdasarkan hasil MCU & DCU yang berlaku) dan sehat secara mental",
    "4. Saya menggunakan APD (Alat Pelindung Diri) yang sesuai",
    "5. Saya telah mengindentifikasi bahaya dan risiko sebelum pekerjaan dilaksanakan (Last Minute Risk Assessment)",
    "6. Saya melaporkan setiap kondisi abnormal/anomali yang berbahaya kepada atasan untuk ditanggulangi",
    "7. Saya memastikan permit to work yang sesuai telah tersedia dan dilaksanakan",
    "8. Saya menjaga kebersihan dan kerapihan loaksi kerja",
    "9. Saya melaksanakan perilaku kunci yang disyaratkan dalam 10 elemen CLSR"
]

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
                return redirect(url_for('main.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@bp.route('/', methods=['GET'])
@login_required
def index():
    name = request.args.get('name', '').strip()
    division = request.args.get('division', '').strip()
    site = request.args.get('site', '').strip()
    sub_location = request.args.get('sub_location', '').strip()
    status = request.args.get('status', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '').strip()
    
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

    distinct_divisions = sorted(set(r.division for r in TOFSReport.query.with_entities(TOFSReport.division).distinct()))
    distinct_sites = sorted(set(r.site for r in TOFSReport.query.with_entities(TOFSReport.site).distinct()))
    distinct_status = sorted(set(r.status for r in TOFSReport.query.with_entities(TOFSReport.status).distinct()))

    return render_template('main/index.html',
                           reports=reports,
                           distinct_divisions=distinct_divisions,
                           distinct_sites=distinct_sites,
                           distinct_status=distinct_status,
                           filters=request.args)

@bp.route('/add', methods=['GET', 'POST'])
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
        perilaku_wajib = request.form.get('perilaku_wajib')
        site_supervisor = bool(request.form.get('site_supervisor'))
        site_superintendent = bool(request.form.get('site_superintendent'))
        status = request.form['status']

        if not all([name, division, site, sub_location, date, issue_description, follow_up, clsr_terkait, perilaku_wajib, status]):
            flash('Semua field wajib diisi!', 'danger')
            return redirect(url_for('main.add'))
        if 'site_supervisor' not in request.form or 'site_superintendent' not in request.form:
            flash('Checkbox Site Supervisor dan Superintendent wajib dicentang!', 'danger')
            return redirect(url_for('main.add'))
        
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
            perilaku_wajib=perilaku_wajib,
            site_supervisor=site_supervisor,
            site_superintendent=site_superintendent,
            user_id=current_user.id
        )
        db.session.add(report)
        db.session.commit()
        return redirect(url_for('main.index'))

    return render_template('main/form.html')

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
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

        perilaku_terpilih = request.form.getlist('perilaku_wajib')
        report.perilaku_wajib = ','.join(perilaku_terpilih)  

        report.site_supervisor = True if request.form.get('site_supervisor') == '1' else False
        report.site_superintendent = True if request.form.get('site_superintendent') == '1' else False
        
        db.session.commit()
        flash('Data TOFS berhasil diperbarui.', 'success')
        return redirect(url_for('main.index'))
    
    report.perilaku_wajib_list = report.perilaku_wajib.split(',') if report.perilaku_wajib else []
    return render_template('main/edit.html', report=report, clsr_options=CLSR_OPTIONS, perilaku_options=PERILAKU_WAJIB_OPTIONS)

@bp.route('/delete/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'super admin')
def delete(id):
    report = TOFSReport.query.get_or_404(id)
    db.session.delete(report)
    db.session.commit()
    flash('Data TOFS berhasil dihapus.', 'success')
    return redirect(url_for('main.index'))

@bp.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    start_of_year = date(today.year, 1, 1)
    three_years_ago = today.replace(year=today.year - 3)

    # Ambil filter dari query string
    selected_period = request.args.get('period', '')
    filter_site = request.args.get('site','')
    filter_division = request.args.get('division','')
    filter_month = request.args.get('month', '')
    filter_year = request.args.get('year', '')
    filter_status = request.args.get('status','')

    # Ambil semua data (query builder)
    reports = TOFSReport.query

    # Terapkan filter berdasarkan site, division, status, tahun
    if filter_site:
        reports = reports.filter_by(site=filter_site)
    if filter_division:
        reports = reports.filter_by(division=filter_division)
    if filter_status:
        reports = reports.filter_by(status=filter_status)
    if filter_year and filter_year.isdigit():
        reports = reports.filter(db.extract('year', TOFSReport.date) == int(filter_year))

    # Terapkan filter bulan jika bukan 'All'
    if filter_month and filter_month != 'All':
        month_map = {
            'Januari': 1,
            'Februari': 2,
            'Maret': 3,
            'April': 4,
            'Mei': 5,
            'Juni': 6,
            'Juli': 7,
            'Agustus': 8,
            'September': 9,
            'Oktober': 10,
            'November': 11,
            'Desember': 12
        }
        month_num = month_map.get(filter_month)
        if month_num:
            reports = reports.filter(db.extract('month', TOFSReport.date) == month_num)

    # Filter periode
    if selected_period == '1_year':
        start_date = today - timedelta(days=365)
        reports = reports.filter(TOFSReport.date >= start_date)
    elif selected_period == '6_months':
        start_date = today - timedelta(days=182)
        reports = reports.filter(TOFSReport.date >= start_date)
    elif selected_period == 'year_to_date':
        reports = reports.filter(TOFSReport.date >= start_of_year)
    elif selected_period == '3_years':
        reports = reports.filter(TOFSReport.date >= three_years_ago)

    # Eksekusi query
    reports = reports.all()

    # Variabel dasar
    total_tofs = len(reports)
    site_counts = Counter([r.site for r in reports])
    counts_status = Counter([r.status for r in reports])
    counts_by_name = Counter([r.name for r in reports])
    clsr_counter = Counter([r.clsr_terkait for r in reports if r.clsr_terkait])

    # Chart by time
    monthly_counts = defaultdict(int)
    for r in reports:
        month_str = r.date.strftime('%b %Y')  # Contoh: Jan 2025
        monthly_counts[month_str] += 1

    # Urutkan bulan
    sorted_months = sorted(monthly_counts.keys(), key=lambda x: datetime.strptime(x, '%b %Y'))
    counts_sorted = [monthly_counts[m] for m in sorted_months]

    # Data untuk filter form
    all_reports = TOFSReport.query.all()
    sites = sorted(set(r.site for r in all_reports))
    divisions = sorted(set(r.division for r in all_reports))
    statuses = sorted(set(r.status for r in all_reports))
    years = sorted(set(r.date.year for r in all_reports))

    month_names_indo = [
        '', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
        'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
    ]
    months = [(name, name) for name in month_names_indo]  # value dan label sama

    return render_template('main/dashboard.html',
                           total_tofs=total_tofs,
                           site_counts=site_counts,
                           counts_status=counts_status,
                           counts_by_name=counts_by_name,
                           clsr_labels=list(clsr_counter.keys()),
                           clsr_values=list(clsr_counter.values()),
                           months_sorted=sorted_months,
                           counts_sorted=counts_sorted,
                           selected_period=selected_period,
                           # Filter values
                           filter_site=filter_site,
                           filter_division=filter_division,
                           filter_month=filter_month,
                           filter_status=filter_status,
                           filter_year=filter_year,
                           # Untuk select options
                           sites=sites,
                           divisions=divisions,
                           statuses=statuses,
                           years=years,
                           months=months)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        full_name = request.form['full_name']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = 'pengguna'
        work_location = request.form.get('work_location', '')

        if User.query.filter_by(username=username).first():
            flash('Username sudah digunakan.', 'danger')
            return redirect(url_for('main.register'))

        if User.query.filter_by(email=email).first():
            flash('Email sudah digunakan.', 'danger')
            return redirect(url_for('main.register'))

        user = User(full_name=full_name, username=username, email=email, role=role, work_location=work_location)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()
        flash('Registrasi berhasil, silakan login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('main/register.html')

@bp.route('/users')
@login_required
@role_required('super admin')
def users():
    page = request.args.get('page', 1, type=int)
    query = User.query

    search_query = request.args.get('q')
    if search_query:
        query = query.filter(
            (User.full_name.ilike(f'%{search_query}%')) |
            (User.username.ilike(f'%{search_query}%')) |
            (User.email.ilike(f'%{search_query}%'))
        )

    users = query.order_by(User.full_name).paginate(page=page, per_page=10)
    return render_template('main/users.html', users=users)

@bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@role_required('super admin')
def add_user():
    if request.method == 'POST':
        full_name = request.form['full_name']
        username = request.form['username']
        email = request.form['email']
        role = request.form['role']
        work_location = request.form.get('work_location', '')
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('Username sudah digunakan.', 'danger')
            return redirect(url_for('main.add_user'))

        if User.query.filter_by(email=email).first():
            flash('Email sudah digunakan.', 'danger')
            return redirect(url_for('main.add_user'))

        user = User(full_name=full_name, username=username, email=email, role=role, work_location=work_location)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()
        flash('User berhasil ditambahkan.', 'success')
        return redirect(url_for('main.users'))

    return render_template('main/add_user.html')

@bp.route('/users/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('super admin')
def edit_user(id):
    user = User.query.get_or_404(id)
    if request.method == 'POST':
        user.full_name = request.form['full_name']
        user.username = request.form['username']
        user.email = request.form['email']
        user.role = request.form['role']
        user.work_location = request.form.get('work_location', '')
        if request.form['password']:
            user.set_password(request.form['password'])
        db.session.commit()
        flash('User berhasil diperbarui.', 'success')
        return redirect(url_for('main.users'))

    return render_template('main/edit_user.html', user=user)

@bp.route('/users/delete/<int:id>', methods=['POST'])
@login_required
@role_required('super admin')
def delete_user(id):
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash('User berhasil dihapus.', 'success')
    return redirect(url_for('main.users'))

@bp.route('/download_excel')
@login_required
def download_excel():
    name = request.args.get('name', '').strip()
    division = request.args.get('division', '').strip()
    site = request.args.get('site', '').strip()
    sub_location = request.args.get('sub_location', '').strip()
    status = request.args.get('status', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    search_query = request.args.get('q', '').strip()

    query = TOFSReport.query.order_by(TOFSReport.date.desc())
    filters = []

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

    reports = query.all()

    # Ambil semua field kecuali 'id'
    data = []
    for r in reports:
        data.append({
            'Card Number': r.card_number,
            'Name': r.name,
            'Division': r.division,
            'Site': r.site,
            'Sub Location': r.sub_location,
            'Date': r.date.strftime('%Y-%m-%d'),
            'Issue Description': r.issue_description,
            'Follow Up': r.follow_up or '',
            'CLSR Terkait': r.clsr_terkait or '',
            'Perilaku Wajib': r.perilaku_wajib or '',
            'Site Supervisor': 'Ya' if str(r.site_supervisor).strip() in ['1', 'True', 'true', 'ya', 'Ya'] else 'Tidak',
            'Site Superintendent': 'Ya' if str(r.site_superintendent).strip() in ['1', 'True', 'true', 'ya', 'Ya'] else 'Tidak',
            'Status': r.status
        })

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='TOFS Reports')

        workbook  = writer.book
        worksheet = writer.sheets['TOFS Reports']
         # Buat format wrap text untuk kolom tertentu
        wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})

        # Terapkan format untuk setiap kolom
        for idx, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2

            # Hanya wrap text untuk kolom Issue Description dan Follow Up
            if col in ['Issue Description', 'Follow Up']:
                worksheet.set_column(idx, idx, max_len, wrap_format)
            else:
                worksheet.set_column(idx, idx, max_len)

        worksheet.set_column('A:A', 15)   # Card Number
        worksheet.set_column('B:B', 20)   # Name
        worksheet.set_column('C:C', 15)   # Division
        worksheet.set_column('D:D', 20)   # Site
        worksheet.set_column('E:E', 20)   # Sub Location
        worksheet.set_column('F:F', 12)   # Date
        worksheet.set_column('G:G', 40)   # Issue Description
        worksheet.set_column('H:H', 40)   # Follow Up
        worksheet.set_column('I:I', 25)   # CLSR Terkait
        worksheet.set_column('J:J', 45)   # Perilaku Wajib
        worksheet.set_column('K:K', 20)   # Site Supervisor
        worksheet.set_column('L:L', 22)   # Site Superintendent
        worksheet.set_column('M:M', 12)   # Status
    output.seek(0)

    filename = f'tofs_reports_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        download_name=filename,
        as_attachment=True
    )

