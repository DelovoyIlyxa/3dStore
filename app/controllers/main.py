# controllers/main.py
from flask import Blueprint, redirect, url_for, request, current_app

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'unknown')
    current_app.logger.info(f"[MAIN] Корневой запрос: ip={ip}, user_agent='{user_agent[:50]}...', редирект в shop.catalog")
    return redirect(url_for('shop.catalog'))

@main_bp.route('/test-log')
def test_log():
    current_app.logger.info("✅ Тестовый лог: INFO")
    current_app.logger.warning("⚠️ Тестовый лог: WARNING")
    current_app.logger.error("❌ Тестовый лог: ERROR")
    return "Проверьте консоль — должны быть логи!"
