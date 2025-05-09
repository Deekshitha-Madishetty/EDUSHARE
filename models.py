# /EDUSHARE/models.py

# Import the db object *instance* created in app.py
from app import db, login_manager # Import login_manager here as well for user_loader if needed
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# User Model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True) # Existing

    # Relationship to owned books (using your existing name 'books')
    books = db.relationship('Book', backref='owner', lazy='dynamic') # Changed lazy to 'dynamic' for potential filtering

    # --- NEW: Relationships for transactions and notifications ---
    sent_requests = db.relationship('Transaction',
                                    foreign_keys='Transaction.requester_id',
                                    backref='requester',
                                    lazy='dynamic')
    received_requests = db.relationship('Transaction',
                                        foreign_keys='Transaction.owner_id',
                                        backref='book_owner', # Use specific backref name
                                        lazy='dynamic')
    notifications = db.relationship('Notification',
                                    backref='user',
                                    lazy='dynamic',
                                    order_by="Notification.timestamp.desc()") # Order notifications for user

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def unread_notifications_count(self):
        """Helper method to get count of unread notifications."""
        return Notification.query.filter_by(user_id=self.id, is_read=False).count()

    def __repr__(self):
        return f'<User {self.username}>'

# Book Model
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=True)
    is_donation = db.Column(db.Boolean, default=False, nullable=False)
    # status = db.Column(db.String(20), default='available', nullable=False) # Existing - GOOD! Add 'pending' state
    # Let's ensure possible states are: 'available', 'pending', 'sold' (sold/donated are terminal)
    status = db.Column(db.String(20), default='available', nullable=False, index=True) # Added index
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True) # Added index

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Existing FK

    # --- NEW: Relationship to track transactions involving this book ---
    transactions = db.relationship('Transaction', backref='book', lazy='dynamic')

    def __repr__(self):
        return f'<Book {self.title}>'

# --- NEW: Transaction Model ---
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False, index=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    transaction_type = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False, index=True)
    request_timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    action_timestamp = db.Column(db.DateTime, nullable=True)
    completion_timestamp = db.Column(db.DateTime, nullable=True)
    # --- NEW FIELD ---
    # Store the contact info the seller provided specifically for this transaction
    seller_contact_info = db.Column(db.String(150), nullable=True) # Store phone, email, etc.

    def __repr__(self):
        return f'<Transaction {self.id} for Book {self.book_id} ({self.status})>'


# --- NEW: Notification Model ---
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True) # The user TO notify
    related_transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=True, index=True)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)

    
    def __repr__(self):
        return f'<Notification {self.id} for User {self.user_id} Read: {self.is_read}>'

