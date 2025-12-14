# controllers/auth.py (улучшенная версия)

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from app.models import User
from app import db
import re

auth_bp = Blueprint('auth', __name__)

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)

        current_app.logger.info(f"[AUTH] Регистрация: начало обработки для email={email}, ip={ip}")

        # Валидация
        if not email or not password:
            current_app.logger.warning(f"[AUTH] Регистрация отклонена: пустой email/пароль, ip={ip}")
            flash("Email и пароль обязательны", "error")
            return render_template('auth/register.html')
        
        if not is_valid_email(email):
            current_app.logger.warning(f"[AUTH] Регистрация отклонена: некорректный email='{email}', ip={ip}")
            flash("Некорректный email", "error")
            return render_template('auth/register.html')

        if len(password) < 6:
            current_app.logger.warning(f"[AUTH] Регистрация отклонена: пароль короче 6 символов, email={email}, ip={ip}")
            flash("Пароль должен быть не короче 6 символов", "error")
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            current_app.logger.warning(f"[AUTH] Регистрация отклонена: email уже занят, email={email}, ip={ip}")
            flash("Пользователь с таким email уже существует", "error")
            return render_template('auth/register.html')

        # Создаём пользователя
        role = request.form.get('role', 'user')
        try:
            user = User(email=email, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            current_app.logger.info(f"[AUTH] Регистрация успешна: email={email}, role={role}, user_id={user.id}, ip={ip}")
            flash("✅ Регистрация успешна! Теперь вы можете войти.", "success")
            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"[AUTH] Ошибка при регистрации: email={email}, role={role}, ip={ip}, error={str(e)}", exc_info=True)
            flash("Произошла внутренняя ошибка. Попробуйте позже.", "error")
            return render_template('auth/register.html')

    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)

        current_app.logger.info(f"[AUTH] Вход: начало обработки для email={email}, ip={ip}")

        if not email or not password:
            current_app.logger.warning(f"[AUTH] Вход отклонён: пустой email/пароль, ip={ip}")
            flash("Заполните email и пароль", "error")
            return render_template('auth/login.html')

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            current_app.logger.warning(f"[AUTH] Вход отклонён: неверные учётные данные, email={email}, ip={ip}")
            flash("❌ Неверный email или пароль", "error")
            return render_template('auth/login.html')

        try:
            from flask_login import login_user
            login_user(user)
            current_app.logger.info(f"[AUTH] Вход успешен: user_id={user.id}, email={email}, role={user.role}, ip={ip}")
            flash("✅ Добро пожаловать, " + user.email.split('@')[0] + "!", "success")
            return redirect(url_for('shop.catalog'))  # сразу в каталог

        except Exception as e:
            current_app.logger.error(f"[AUTH] Ошибка при входе: email={email}, ip={ip}, error={str(e)}", exc_info=True)
            flash("Произошла ошибка при входе. Попробуйте позже.", "error")
            return render_template('auth/login.html')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    try:
        from flask_login import logout_user, current_user
        user_id = current_user.id if current_user.is_authenticated else 'anonymous'
        email = current_user.email if current_user.is_authenticated else 'anonymous'

        logout_user()
        current_app.logger.info(f"[AUTH] Выход: user_id={user_id}, email={email}, ip={ip}")
        flash("Вы вышли из аккаунта", "info")
    except Exception as e:
        current_app.logger.error(f"[AUTH] Ошибка при выходе: ip={ip}, error={str(e)}", exc_info=True)
        flash("Произошла ошибка при выходе.", "error")

    return redirect(url_for('main.index'))
