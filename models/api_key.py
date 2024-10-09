# models/api_key.py

from flask_sqlalchemy import SQLAlchemy
import uuid

db = SQLAlchemy()

class APIKey(db.Model):
    __tablename__ = 'api_keys'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    owner = db.Column(db.String(100), nullable=False)
    active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<APIKey {self.key} owned by {self.owner}>'
