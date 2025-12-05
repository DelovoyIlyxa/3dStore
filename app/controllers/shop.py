# controllers/shop.py
from flask import Blueprint, render_template, request, redirect, url_for, send_from_directory, current_app, flash
from flask_login import login_required, current_user

from app import db
from slugify import slugify
import os

from app.models import Product
from app.models import Purchase

shop_bp = Blueprint('shop', __name__)

@shop_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if current_user.role != 'seller':
        flash("Только продавцы могут загружать модели", "error")
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        print("🔍 POST данные:", list(request.form.keys()))
        print("📁 Файлы:", list(request.files.keys()))
        title = request.form['title']
        description = request.form.get('description', '')
        price = float(request.form['price'])
        
        file = request.files['file']
        preview = request.files.get('preview')  # может быть None

        # Обработка 3D-файла (обязательно!!)
        if not file or not file.filename:
            return "3D-файл обязателен", 400

        # Генерируем безопасные имена
        base_name = slugify(title) + '_' + str(current_user.id)
        
        # Сохраняем 3D файл
        file_ext = os.path.splitext(file.filename)[1].lower()
        file_name = base_name + '_model' + file_ext
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_name)
        file.save(file_path)

        # Сохраняем превью (если загружено)
        preview_name = None
        if preview and preview.filename:
            img_ext = os.path.splitext(preview.filename)[1].lower()
            if img_ext in ['.jpg', '.jpeg', '.png', '.webp']:
                preview_name = base_name + '_preview' + img_ext
                preview_path = os.path.join(current_app.config['UPLOAD_FOLDER'], preview_name)
                preview.save(preview_path)

        # Сохраняем в БД
        product = Product(
            title=title,
            description=description,
            price=price,
            file_path=file_name,
            preview_image=preview_name,  # может быть None
            seller_id=current_user.id
        )
        db.session.add(product)
        db.session.commit()
        flash("Модель успешно загружена!", "success")
        return redirect(url_for('shop.catalog'))
    
    return render_template('seller/upload.html')

@shop_bp.route('/')
def catalog():
    # Получаем все модели, сортируем по дате (новые выше)
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('shop/catalog.html', products=products)

@shop_bp.route('/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('shop/product_detail.html', product=product)

@shop_bp.route('/<int:product_id>/download')
@login_required
def download_file(product_id):
    product = Product.query.get_or_404(product_id)
    
    has_access = (
        current_user.role == 'admin' or
        product.seller_id == current_user.id or
        Purchase.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    )
    if not has_access:
        return "Доступ запрещён", 403

    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
    file_path = os.path.join(upload_folder, product.file_path)

    if not os.path.isfile(file_path):
        return "Файл не найден", 404

    return send_from_directory(
        os.path.dirname(file_path),
        os.path.basename(file_path),
        as_attachment=True
    )
    
# УСТАРЕЛО
# @shop_bp.route('/<int:product_id>/buy')
# @login_required
# def buy_product(product_id):
#     product = Product.query.get_or_404(product_id)
    
#     # Проверка: не купил ли уже?
#     if Purchase.query.filter_by(user_id=current_user.id, product_id=product_id).first():
#         return "Вы уже купили эту модель!", 400

#     # Создаём покупку
#     purchase = Purchase(user_id=current_user.id, product_id=product_id)
#     db.session.add(purchase)
#     db.session.commit()

#     return redirect(url_for('shop.product_detail', product_id=product_id))

@shop_bp.route('/<int:product_id>/checkout', methods=['POST'])
@login_required
def checkout(product_id):
    product = Product.query.get_or_404(product_id)
    
    # МОК ОПЛАТЫ: всегда успешно
    purchase = Purchase(user_id=current_user.id, product_id=product_id)
    db.session.add(purchase)
    db.session.commit()
    
    # Редирект на страницу успеха
    return redirect(url_for('shop.payment_success', product_id=product_id))


@shop_bp.route('/payment/success/<int:product_id>')
def payment_success(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('shop/payment_success.html', product=product)

@shop_bp.route('/<int:product_id>/download-trigger', methods=['POST'])
@login_required
def download_trigger(product_id):
    # Просто редиректим на скачивание (беез JS для единообразия)
    return redirect(url_for('shop.download_file', product_id=product_id))
