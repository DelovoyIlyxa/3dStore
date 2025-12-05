# controllers/auth.py
from flask import Blueprint, render_template, request, redirect, url_for
from app.models import User
from app import db, login_manager
from flask_login import login_user, logout_user

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if User.query.filter_by(email=email).first():
            return render_template('auth/register.html', error="Email уже занят")

        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        return redirect(url_for('main.index'))

    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.index'))
        else:
            return render_template('auth/login.html', error="Неверный email или пароль")

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))
