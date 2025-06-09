from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, current_user
from app.models import db, User

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Login berhasil!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Login gagal. Periksa username/password.', 'danger')

    return render_template('auth/login.html')  # Jangan lupa pathnya

@auth.route('/logout')
def logout():
    logout_user()
    flash('Logout berhasil.', 'success')
    return redirect(url_for('auth.login'))
