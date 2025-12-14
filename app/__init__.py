# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
import logging

# Разрешаем .glb, .gltf и другие 3D-форматы
from werkzeug.utils import secure_filename
import mimetypes

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(
        __name__,
        template_folder='views',   # шаблоны в корне/views/
        static_folder='static'    # статика в корне/static/
    )

    # Настройка логирования (раньше — чтобы залогировать инициализацию)
    # Уровень по умолчанию — INFO, лог в консоль
        # 🔥 ГАРАНТИРОВАННО включаем INFO-логи в консоль
    logging.getLogger().setLevel(logging.INFO)  # ← корневой логгер
    app.logger.setLevel(logging.INFO)          # ← логгер приложения

    # Опционально: убедимся, что StreamHandler есть и выводит всё
    if not app.logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '[%(asctime)s] %(levelname)-8s %(name)s: %(message)s'
        ))
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)

    # Конфигурация
    app.secret_key = 'super-secret-key-for-3d-store-2025'
    base_dir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(base_dir, '..', 'app.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    UPLOAD_FOLDER = os.path.join(base_dir, 'static', 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    app.logger.info(f"[APP] Приложение инициализировано: base_dir={base_dir}")
    app.logger.info(f"[APP] База данных: {app.config['SQLALCHEMY_DATABASE_URI']}")
    app.logger.info(f"[APP] Папка загрузок: {UPLOAD_FOLDER}")

    # Добавляем MIME-типы для 3D-форматов
    mime_additions = {
        '.glb': 'model/gltf-binary',
        '.gltf': 'model/gltf+json',
        '.obj': 'application/octet-stream',
        '.fbx': 'application/octet-stream'
    }
    for ext, mime in mime_additions.items():
        mimetypes.add_type(mime, ext)
        app.logger.info(f"[APP] MIME-тип добавлен: {ext} → {mime}")

    # Разрешённые расширения
    app.config['STATIC_EXTENSIONS'] = {'.glb', '.gltf', '.obj', '.fbx', '.png', '.jpg', '.jpeg', '.webp'}
    app.logger.info(f"[APP] Разрешённые расширения: {sorted(app.config['STATIC_EXTENSIONS'])}")

    # Инициализация расширений с приложением
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    app.logger.info("[APP] Расширения инициализированы: SQLAlchemy, Flask-Login")

    # Загрузчик пользователя
    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        user = User.query.get(int(user_id))
        if user:
            app.logger.debug(f"[APP] Пользователь загружен: id={user_id}, email={user.email}, role={user.role}")
        else:
            app.logger.warning(f"[APP] Пользователь не найден по id={user_id}")
        return user

    # Регистрация Blueprints
    from app.controllers.main import main_bp
    from app.controllers.auth import auth_bp
    from app.controllers.shop import shop_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(shop_bp, url_prefix='/shop')
    app.logger.info("[APP] Blueprints зарегистрированы: main, auth, shop")

    # Создание БД и тестовые данные
    with app.app_context():
        app.logger.info("[APP] Создание/миграция базы данных...")
        db.create_all()
        app.logger.info("[APP] База данных готова")

        # Тестовый продавец
        test_email = 'seller@example.com'
        if not User.query.filter_by(email=test_email).first():
            seller = User(email=test_email, role='seller')
            seller.set_password('123456')
            db.session.add(seller)
            db.session.commit()
            app.logger.info(f"[APP] Создан тестовый продавец: id={seller.id}, email={test_email}")
        else:
            seller = User.query.filter_by(email=test_email).first()
            app.logger.info(f"[APP] Тестовый продавец уже существует: id={seller.id}, email={test_email}")

    app.logger.info("[APP] Приложение успешно создано и готово к запуску")
    return app
