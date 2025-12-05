# app/models/purchase.py
from datetime import datetime
from app import db

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связи
    user = db.relationship('User', backref='purchases')
    product = db.relationship('Product', backref='purchases')
