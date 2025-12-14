# app/models/review.py
from datetime import datetime
from app import db

class Review(db.Model):
    __tablename__ = 'review'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1–5
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связи
    user = db.relationship('User', backref=db.backref('reviews', lazy='dynamic'))
    product = db.relationship('Product', backref=db.backref('reviews', lazy='dynamic'))

    __table_args__ = (db.UniqueConstraint('user_id', 'product_id', name='_user_product_uc'),)

    def __repr__(self):
        return f'<Review {self.user.email} → {self.product.title}: {self.rating}★>'