# controllers/shop.py
from flask import Blueprint, render_template, request, redirect, url_for, send_from_directory, current_app, flash
from flask_login import login_required, current_user
from sqlalchemy import func, desc, or_
from urllib.parse import quote

from app import db
from slugify import slugify
import os

from app.models import Product, Purchase, Review

shop_bp = Blueprint('shop', __name__)

@shop_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    current_app.logger.info(f"[SHOP] Upload: начало, user_id={current_user.id}, role={current_user.role}, ip={ip}")
    
    if current_user.role != 'seller':
        current_app.logger.warning(f"[SHOP] Upload отклонён: недостаточно прав, user_id={current_user.id}, ip={ip}")
        flash("Только продавцы могут загружать модели", "error")
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description', '')
        price = float(request.form['price'])
        
        file = request.files['file']
        preview = request.files.get('preview')

        if not file or not file.filename:
            current_app.logger.warning(f"[SHOP] Upload отклонён: 3D-файл не загружен, user_id={current_user.id}, ip={ip}")
            return "3D-файл обязателен", 400

        base_name = slugify(title) + '_' + str(current_user.id)
        file_ext = os.path.splitext(file.filename)[1].lower()
        file_name = base_name + '_model' + file_ext
        upload_folder = current_app.config['UPLOAD_FOLDER']
        file_path = os.path.join(upload_folder, file_name)

        try:
            file.save(file_path)
            current_app.logger.info(f"[SHOP] Upload: 3D-файл сохранён, user_id={current_user.id}, file_path={file_name}, size={os.path.getsize(file_path)} bytes")

            preview_name = None
            if preview and preview.filename:
                img_ext = os.path.splitext(preview.filename)[1].lower()
                if img_ext in ['.jpg', '.jpeg', '.png', '.webp']:
                    preview_name = base_name + '_preview' + img_ext
                    preview_path = os.path.join(upload_folder, preview_name)
                    preview.save(preview_path)
                    current_app.logger.info(f"[SHOP] Upload: превью сохранено, user_id={current_user.id}, preview_path={preview_name}")

            product = Product(
                title=title,
                description=description,
                price=price,
                file_path=file_name,
                preview_image=preview_name,
                seller_id=current_user.id
            )
            db.session.add(product)
            db.session.commit()

            current_app.logger.info(f"[SHOP] Upload успешен: product_id={product.id}, user_id={current_user.id}, title='{title}', file_path={file_name}")
            flash("Модель успешно загружена!", "success")
            return redirect(url_for('shop.catalog'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"[SHOP] Upload ошибка: user_id={current_user.id}, title='{title}', ip={ip}, error={str(e)}", exc_info=True)
            flash("Произошла ошибка при загрузке. Попробуйте позже.", "error")
            return render_template('seller/upload.html')

    return render_template('seller/upload.html')

@shop_bp.route('/')
def catalog():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    query = request.args.get('q', '').strip()
    current_app.logger.info(f"[SHOP] Каталог: запрос, ip={ip}, query='{query}'")

    base_query = db.session.query(
        Product,
        func.avg(Review.rating).label('avg_rating'),
        func.count(Review.id).label('review_count')
    ).outerjoin(Review).group_by(Product.id).order_by(Product.created_at.desc())

    if query:
        base_query = base_query.filter(
            or_(
                Product.title.ilike(f'%{query}%'),
                Product.description.ilike(f'%{query}%')
            )
        )

    products = base_query.all()

    return render_template('shop/catalog.html', products=products, search_query=query)

@shop_bp.route('/<int:product_id>')
def product_detail(product_id):
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    current_app.logger.info(f"[SHOP] Просмотр товара: product_id={product_id}, ip={ip}, user_id={current_user.id if current_user.is_authenticated else 'anon'}")
    
    product = Product.query.get_or_404(product_id)
    
    avg_rating = db.session.query(func.avg(Review.rating))\
        .filter(Review.product_id == product_id)\
        .scalar() or 0.0

    user_review = None
    if current_user.is_authenticated:
        user_review = Review.query.filter_by(
            user_id=current_user.id,
            product_id=product_id
        ).first()
        
    reviews = Review.query\
        .filter_by(product_id=product_id)\
        .order_by(desc(Review.created_at))\
        .limit(10)\
        .all()
        
    upload_folder = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_folder, product.file_path)
    
    file_size_mb = 0.0
    if os.path.isfile(file_path):
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

    return render_template(
        'shop/product_detail.html',
        product=product,
        file_size_mb=file_size_mb,
        avg_rating=float(avg_rating),
        user_review=user_review,
        reviews=reviews
    )

@shop_bp.route('/<int:product_id>/download')
@login_required
def download_file(product_id):
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    current_app.logger.info(f"[SHOP] Запрос скачивания: product_id={product_id}, user_id={current_user.id}, ip={ip}")
    
    product = Product.query.get_or_404(product_id)
    
    has_access = (
        current_user.role == 'admin' or
        product.seller_id == current_user.id or
        Purchase.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    )
    if not has_access:
        current_app.logger.warning(f"[SHOP] Скачивание отклонено: нет доступа, user_id={current_user.id}, product_id={product_id}, ip={ip}")
        return "Доступ запрещён", 403

    upload_folder = current_app.config['UPLOAD_FOLDER']
    file_path_in_db = product.file_path
    full_file_path = os.path.join(upload_folder, file_path_in_db)

    if not os.path.isfile(full_file_path):
        current_app.logger.error(f"[SHOP] Файл отсутствует при скачивании: product_id={product_id}, file_path={full_file_path}, DB={file_path_in_db}, ip={ip}")
        return "Файл был удалён или повреждён", 404

    safe_download_name = os.path.basename(file_path_in_db)
    file_size = os.path.getsize(full_file_path)

    current_app.logger.info(f"[SHOP] Скачивание разрешено: product_id={product.id}, user_id={current_user.id}, file_path={file_path_in_db}, size={file_size} bytes, ip={ip}")
    
    return send_from_directory(
        directory=upload_folder,
        path=file_path_in_db,
        as_attachment=True,
        download_name=safe_download_name
    )

@shop_bp.route('/<int:product_id>/checkout', methods=['POST'])
@login_required
def checkout(product_id):
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    current_app.logger.info(f"[SHOP] Оплата: product_id={product_id}, user_id={current_user.id}, ip={ip}")
    
    product = Product.query.get_or_404(product_id)
    
    try:
        purchase = Purchase(user_id=current_user.id, product_id=product_id)
        db.session.add(purchase)
        db.session.commit()
        
        current_app.logger.info(f"[SHOP] Покупка успешна: purchase_id={purchase.id}, user_id={current_user.id}, product_id={product_id}, ip={ip}")
        return redirect(url_for('shop.payment_success', product_id=product_id))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[SHOP] Ошибка покупки: user_id={current_user.id}, product_id={product_id}, ip={ip}, error={str(e)}", exc_info=True)
        flash("Ошибка при оформлении покупки", "error")
        return redirect(url_for('shop.product_detail', product_id=product_id))

@shop_bp.route('/payment/success/<int:product_id>')
def payment_success(product_id):
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    current_app.logger.info(f"[SHOP] Страница успеха: product_id={product_id}, ip={ip}")
    product = Product.query.get_or_404(product_id)
    return render_template('shop/payment_success.html', product=product)

@shop_bp.route('/<int:product_id>/download-trigger', methods=['POST'])
@login_required
def download_trigger(product_id):
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    current_app.logger.info(f"[SHOP] Триггер скачивания: product_id={product_id}, user_id={current_user.id}, ip={ip}")
    return redirect(url_for('shop.download_file', product_id=product_id))

@shop_bp.route('/<int:product_id>/review', methods=['POST'])
@login_required
def add_review(product_id):
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    current_app.logger.info(f"[SHOP] Добавление отзыва: product_id={product_id}, user_id={current_user.id}, ip={ip}")
    
    product = Product.query.get_or_404(product_id)

    purchase = Purchase.query.filter_by(
        user_id=current_user.id,
        product_id=product_id
    ).first()

    if not purchase:
        current_app.logger.warning(f"[SHOP] Отзыв отклонён: не куплено, user_id={current_user.id}, product_id={product_id}, ip={ip}")
        flash("Оценить можно только купленные модели", "error")
        return redirect(url_for('shop.product_detail', product_id=product_id))

    if Review.query.filter_by(user_id=current_user.id, product_id=product_id).first():
        current_app.logger.warning(f"[SHOP] Отзыв отклонён: уже оставлен, user_id={current_user.id}, product_id={product_id}, ip={ip}")
        flash("Вы уже оценили эту модель", "info")
        return redirect(url_for('shop.product_detail', product_id=product_id))

    rating = request.form.get('rating', type=int)
    if not rating or rating < 1 or rating > 5:
        current_app.logger.warning(f"[SHOP] Отзыв отклонён: некорректная оценка ({rating}), user_id={current_user.id}, product_id={product_id}, ip={ip}")
        flash("Оценка должна быть от 1 до 5", "error")
        return redirect(url_for('shop.product_detail', product_id=product_id))

    try:
        review = Review(user_id=current_user.id, product_id=product_id, rating=rating)
        db.session.add(review)
        db.session.commit()

        current_app.logger.info(f"[SHOP] Отзыв добавлен: review_id={review.id}, user_id={current_user.id}, product_id={product_id}, rating={rating}, ip={ip}")
        flash("Спасибо за вашу оценку! 🌟", "success")
        return redirect(url_for('shop.product_detail', product_id=product_id))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[SHOP] Ошибка добавления отзыва: user_id={current_user.id}, product_id={product_id}, rating={rating}, ip={ip}, error={str(e)}", exc_info=True)
        flash("Ошибка при отправке отзыва", "error")
        return redirect(url_for('shop.product_detail', product_id=product_id))

@shop_bp.route('/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    current_app.logger.info(f"[SHOP] Редактирование: product_id={product_id}, user_id={current_user.id}, ip={ip}")
    
    product = Product.query.get_or_404(product_id)
    
    if current_user.id != product.seller_id and current_user.role != 'admin':
        current_app.logger.warning(f"[SHOP] Редактирование отклонено: недостаточно прав, user_id={current_user.id}, product_id={product_id}, ip={ip}")
        flash("Доступ запрещён", "error")
        return redirect(url_for('shop.product_detail', product_id=product_id))

    if request.method == 'POST':
        try:
            old_title = product.title
            old_price = product.price
            product.title = request.form['title']
            product.description = request.form.get('description', '')
            product.price = float(request.form['price'])
            db.session.commit()
            
            current_app.logger.info(f"[SHOP] Редактирование успешно: product_id={product.id}, user_id={current_user.id}, old_title='{old_title}', new_title='{product.title}', old_price={old_price}, new_price={product.price}, ip={ip}")
            flash("Модель обновлена", "success")
            return redirect(url_for('shop.product_detail', product_id=product.id))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"[SHOP] Ошибка редактирования: product_id={product_id}, user_id={current_user.id}, ip={ip}, error={str(e)}", exc_info=True)
            flash("Ошибка при обновлении модели", "error")

    return render_template('shop/edit_product.html', product=product)

@shop_bp.route('/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_product(product_id):
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    current_app.logger.info(f"[SHOP] Удаление: product_id={product_id}, user_id={current_user.id}, ip={ip}")
    
    product = Product.query.get_or_404(product_id)
    
    if current_user.id != product.seller_id and current_user.role != 'admin':
        current_app.logger.warning(f"[SHOP] Удаление отклонено: недостаточно прав, user_id={current_user.id}, product_id={product_id}, ip={ip}")
        return "Доступ запрещён", 403

    upload_folder = current_app.config['UPLOAD_FOLDER']
    files_deleted = []

    try:
        if product.file_path:
            file_path = os.path.join(upload_folder, product.file_path)
            if os.path.isfile(file_path):
                os.remove(file_path)
                files_deleted.append(product.file_path)
                current_app.logger.info(f"[SHOP] Удалён 3D-файл: {product.file_path}, product_id={product_id}")

        if product.preview_image:
            preview_path = os.path.join(upload_folder, product.preview_image)
            if os.path.isfile(preview_path):
                os.remove(preview_path)
                files_deleted.append(product.preview_image)
                current_app.logger.info(f"[SHOP] Удалено превью: {product.preview_image}, product_id={product_id}")

        db.session.delete(product)
        db.session.commit()

        current_app.logger.info(f"[SHOP] Модель удалена: product_id={product_id}, user_id={current_user.id}, files_deleted={files_deleted}, ip={ip}")
        flash("Модель удалена", "info")
        return redirect(url_for('shop.catalog'))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[SHOP] Ошибка удаления: product_id={product_id}, user_id={current_user.id}, ip={ip}, error={str(e)}", exc_info=True)
        flash("Ошибка при удалении модели", "error")
        return redirect(url_for('shop.product_detail', product_id=product_id))
