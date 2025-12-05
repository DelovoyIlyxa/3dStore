# models/product.py
from datetime import datetime
from app import db

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    file_path = db.Column(db.String(200), nullable=False)
    preview_image = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.now)

    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller = db.relationship('User', backref=db.backref('products', lazy=True))

    def __repr__(self):
        return f'<Product {self.title} by {self.seller.email}>'
