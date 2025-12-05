# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

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

    # Конфигурация
    app.secret_key = ''
    base_dir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, '..', 'app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    UPLOAD_FOLDER = os.path.join(base_dir, 'static', 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    
    # Добавляем MIME-типы для 3D-форматов
    mimetypes.add_type('model/gltf-binary', '.glb')
    mimetypes.add_type('model/gltf+json', '.gltf')
    mimetypes.add_type('application/octet-stream', '.obj')
    mimetypes.add_type('application/octet-stream', '.fbx')

    # И говорим Flask разрешить эти расширения
    app.config['STATIC_EXTENSIONS'] = {'.glb', '.gltf', '.obj', '.fbx', '.png', '.jpg', '.jpeg', '.webp'}

    # Инициализация расширений с приложением
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Загрузчик пользователя
    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Регистрация Blueprints
    from app.controllers.main import main_bp
    from app.controllers.auth import auth_bp
    from app.controllers.shop import shop_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(shop_bp, url_prefix='/shop')

    # Создание БД
    with app.app_context():
        db.create_all()
        # Тестовый продавец
        if not User.query.filter_by(email='seller@example.com').first():
            seller = User(email='seller@example.com', role='seller')
            seller.set_password('123456')
            db.session.add(seller)
            db.session.commit()
            

    return app
