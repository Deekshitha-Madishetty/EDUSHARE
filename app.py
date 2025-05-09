# /EDUSHARE/app.py
import os
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime 
from flask_migrate import Migrate
from sqlalchemy import or_

# --- App Initialization ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-very-secret-and-random-key'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'edushare.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Initialize Extensions (Instances)---
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

# --- Configure Login Manager ---
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
login_manager.login_message = 'Please log in to access this page.'

# --- Initialize Extensions with App ---

db.init_app(app)
login_manager.init_app(app)
migrate.init_app(app, db)

# --- Import Models and Forms ---
# Import these AFTER extensions are initialized with app
from models import User, Book, Transaction, Notification
from forms import RegistrationForm, LoginForm, AddBookForm



# --- User Loader (Define ONCE) ---
@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    # This is the only load_user function you need
    return User.query.get(int(user_id))


# Context processor for injecting notification count
@app.context_processor
def inject_notification_count():
    """Injects unread notification count into all templates."""
    # This is the only inject_notification_count function you need
    count = 0
    if current_user.is_authenticated:
        try:
            # It's safer to call the method on the user object
            count = current_user.unread_notifications_count()
        except Exception as e:
            app.logger.error(f"Error getting notification count for user {current_user.id}: {e}")
            count = 0 # Default to 0 if there's an error
    return dict(unread_notifications=count)

# Context processor for injecting global variables like 'now'
@app.context_processor # <<< ADD THIS DECORATOR
def inject_global_vars():
    """Injects global variables like current time into all templates."""
    # This is the 'now' function you added
    return dict(
        now=datetime.utcnow() # Pass the current UTC datetime object
    )

# --- Routes ---

@app.route('/')
def index():
    # Filter by status='available' is already correct
    latest_books = Book.query.filter_by(status='available').order_by(Book.date_posted.desc()).limit(6).all()
    return render_template('index.html', title='Home', books=latest_books)

# --- Auth Routes (register, login, logout) - Keep as is ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    # Your existing code is fine
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        # Add phone number during registration if you update the form
        hashed_password = generate_password_hash(form.password.data)
        user = User(username=form.username.data,
                    email=form.email.data,
                    password_hash=hashed_password,
                    # phone_number=form.phone_number.data # If added to form
                   )
        db.session.add(user)
        try:
            db.session.commit()
            flash(f'Account created for {form.username.data}! You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            if 'UNIQUE constraint failed' in str(e):
                 flash('Username or Email already exists. Please choose different ones.', 'danger')
            else:
                 flash(f'Error creating account. Please try again.', 'danger')
            app.logger.error(f"Error creating account: {e}")
    return render_template('register.html', title='Register', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Your existing code is fine
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            if next_page and not next_page.startswith('/'):
                next_page = None
            return redirect(next_page or url_for('index'))
        else:
            flash('Login Unsuccessful. Please check email and password.', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
@login_required
def logout():
    # Your existing code is fine
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# --- Book Management Routes (add, edit, delete) - Keep as is, but ensure status isn't wrongly changed ---
@app.route('/add_book', methods=['GET', 'POST'])
@login_required
def add_book():
    # Your existing code sets status='available' by default, which is correct.
    form = AddBookForm()
    if form.validate_on_submit():
        price_value = form.price.data if form.price.data and form.price.data > 0 else None
        is_donation_flag = form.is_donation.data or (price_value is None)
        book = Book(title=form.title.data,
                    author=form.author.data,
                    description=form.description.data,
                    price=price_value,
                    is_donation=is_donation_flag,
                    owner=current_user, # Use the backref 'owner'
                    status='available') # Explicitly set status on creation
        db.session.add(book)
        try:
            db.session.commit()
            flash(f'Your book has been listed for {"donation" if is_donation_flag else "sale"}!', 'success')
            return redirect(url_for('book_detail', book_id=book.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding book. Please try again.', 'danger')
            app.logger.error(f"Error adding book: {e}")
    return render_template('add_book.html', title='Add/Donate Book', form=form, legend='List a Book') # Changed legend for clarity

@app.route('/book/<int:book_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    if book.owner != current_user:
        abort(403)
    # Prevent editing if book is not available (optional, but good practice)
    if book.status != 'available':
        flash('You cannot edit a book involved in a pending or completed transaction.', 'warning')
        return redirect(url_for('book_detail', book_id=book.id))

    form = AddBookForm(obj=book)
    if form.validate_on_submit():
        book.title = form.title.data
        book.author = form.author.data
        book.description = form.description.data
        book.price = form.price.data if form.price.data and form.price.data > 0 else None
        book.is_donation = form.is_donation.data or (book.price is None)
        # Do NOT change status here - it's managed by transactions
        try:
            db.session.commit()
            flash('Your book listing has been updated!', 'success')
            return redirect(url_for('book_detail', book_id=book.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating book: {e}', 'danger')
            app.logger.error(f"Error updating book {book_id}: {e}")
    return render_template('add_book.html', title='Edit Book Listing', form=form, legend='Update Book Details')

@app.route('/book/<int:book_id>/delete', methods=['POST'])
@login_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    if book.owner != current_user:
        abort(403)
    # Prevent deletion if involved in active transaction? Or cancel transactions?
    # For now, allow deletion but maybe add a check later if needed.
    # Consider implications: what happens to pending requests for this book?
    # Simple approach: Allow deletion, pending requests will fail later if accessed.
    # Better approach: Check for pending/accepted transactions and prevent deletion or cancel them first.
    active_transactions = Transaction.query.filter(
        Transaction.book_id == book.id,
        Transaction.status.in_(['pending', 'accepted'])
    ).count()

    if active_transactions > 0:
        flash('Cannot delete book with active transactions. Please resolve them first.', 'warning')
        return redirect(url_for('book_detail', book_id=book.id))

    try:
        # Manually delete related notifications if desired (or rely on cascade if set up in DB)
        Notification.query.filter(Notification.related_transaction_id.in_(
            db.session.query(Transaction.id).filter_by(book_id=book.id)
        )).delete(synchronize_session='fetch')
        # Manually delete related transactions
        Transaction.query.filter_by(book_id=book.id).delete(synchronize_session='fetch')
        # Now delete the book
        db.session.delete(book)
        db.session.commit()
        flash('Your book listing and related transaction history have been deleted.', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting book: {e}', 'danger')
        app.logger.error(f"Error deleting book {book_id}: {e}")
        return redirect(url_for('book_detail', book_id=book.id))

# --- Browse and Search Routes - Update filters ---
@app.route('/browse_books')
def browse_books():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '').strip() # Get search query, default to empty string, remove whitespace

    # Start base query
    books_query = Book.query.filter_by(is_donation=False, status='available')

    # Apply search filter if a query exists
    if search_query:
        search_pattern = f"%{search_query}%" # Pattern for ILIKE
        books_query = books_query.filter(
            or_(
                Book.title.ilike(search_pattern),
                Book.author.ilike(search_pattern)
                # You could add Book.description.ilike(search_pattern) here too if desired
            )
        )

    # Apply ordering *after* filtering
    books_query = books_query.order_by(Book.date_posted.desc())

    # Paginate the results
    # Make sure per_page matches your desired number of items
    pagination = books_query.paginate(page=page, per_page=9, error_out=False)
    books_for_sale = pagination.items

    # Pass pagination object to the template
    # The search query is available in the template via request.args.get('q')
    return render_template('browse_books.html',
                           title='Browse Books for Sale',
                           books=books_for_sale,
                           pagination=pagination)

@app.route('/browse_donations')
def browse_donations():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '').strip() # Get search query

    # Start base query
    donations_query = Book.query.filter_by(is_donation=True, status='available')

    # Apply search filter if a query exists
    if search_query:
        search_pattern = f"%{search_query}%" # Pattern for ILIKE
        donations_query = donations_query.filter(
            or_(
                Book.title.ilike(search_pattern),
                Book.author.ilike(search_pattern)
                # You could add Book.description.ilike(search_pattern) here too
            )
        )

    # Apply ordering *after* filtering
    donations_query = donations_query.order_by(Book.date_posted.desc())

    # Paginate the results
    # Make sure per_page matches your desired number
    pagination = donations_query.paginate(page=page, per_page=9, error_out=False)
    donated_books = pagination.items

    # Pass pagination object to the template
    return render_template('browse_donations.html',
                           title='Browse Donations',
                           books=donated_books,
                           pagination=pagination)

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    results = []
    pagination = None
    if query:
        search_term = f"%{query}%"
        # Filter by status='available' is correct
        results_query = Book.query.filter(
                Book.status == 'available',
                (Book.title.ilike(search_term) | Book.author.ilike(search_term))
            ).order_by(Book.date_posted.desc())
        pagination = results_query.paginate(page=page, per_page=9)
        results = pagination.items
        if not results:
            flash(f'No available books found matching "{query}".', 'warning')
    else:
        flash('Please enter a title or author to search for.', 'info')
    return render_template('search_results.html', title='Search Results', books=results, pagination=pagination, query=query)


# --- Book Detail Route - Update to pass transaction info ---
@app.route('/book/<int:book_id>')
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    my_transaction = None
    if current_user.is_authenticated:
        # Find if the current user has an active transaction for THIS book
        my_transaction = Transaction.query.filter(
            Transaction.book_id == book.id,
            Transaction.requester_id == current_user.id,
            Transaction.status.in_(['pending', 'accepted']) # Check for ongoing requests by current user
        ).first()

    # Pass both book and potentially the user's active transaction for it
    return render_template('book_detail.html', title=book.title, book=book, my_transaction=my_transaction)


# --- NEW: Transaction and Notification Routes ---

# Combined route for requesting either sale or donation
@app.route('/request_book/<int:book_id>', methods=['POST'])
@login_required
def request_book(book_id):
    book = Book.query.get_or_404(book_id)
    action_type = "donation" if book.is_donation else "sale"

    if book.owner == current_user:
        flash(f'You cannot request your own book.', 'warning')
        return redirect(url_for('book_detail', book_id=book.id))

    if book.status != 'available':
        flash('This book is not currently available for request.', 'warning')
        return redirect(url_for('book_detail', book_id=book.id))

    # Check if user already has a pending/accepted request for THIS book
    existing_transaction = Transaction.query.filter_by(
        book_id=book.id,
        requester_id=current_user.id,
        status='pending' # Only check pending, maybe accepted too? Let's start with just pending.
    ).first()
    if existing_transaction:
        flash('You already have a pending request for this book.', 'info')
        return redirect(url_for('book_detail', book_id=book.id))

    # --- Create Transaction and Notification ---
    transaction = Transaction(
        book_id=book.id,
        requester_id=current_user.id,
        owner_id=book.user_id,
        transaction_type=action_type,
        status='pending'
    )
    # Set book status to pending
    book.status = 'pending'
    db.session.add(transaction)
    db.session.add(book) # Add book to session to save status change

    # Use flush to get transaction ID before creating notification, if needed immediately
    # db.session.flush() # Use cautiously, commits happen later

    # Create notification for the owner
    notif_msg = f"{current_user.username} has requested to {'accept' if action_type == 'donation' else 'buy'} your book: '{book.title}'. Please review in your notifications."
    owner_notification = Notification(
        user_id=book.user_id,
        message=notif_msg,
        # related_transaction_id=transaction.id # Assign after commit ideally, or use flush if required now
    )
    db.session.add(owner_notification)

    try:
        db.session.commit()
        # Now we have the transaction ID, link it to the notification
        owner_notification.related_transaction_id = transaction.id
        db.session.add(owner_notification) # Add again to update FK
        db.session.commit() # Commit the FK update
        flash(f'{action_type.capitalize()} request sent successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error sending request: {str(e)}', 'danger')
        app.logger.error(f"Error in request_book for book {book_id} by user {current_user.id}: {e}")
        # Revert book status if commit fails
        book.status = 'available'
        db.session.add(book)
        db.session.commit()

    return redirect(url_for('book_detail', book_id=book.id))


@app.route('/notifications')
@login_required
def notifications():
    # Fetch notifications ordered by read status then timestamp (newest first) - using order_by in model relationship
    user_notifications = current_user.notifications.all() # Use the relationship

    # Fetch related transaction data efficiently if needed (optional optimization)
    # Example: Load transaction details along with notifications
    notifications_data = []
    for notif in user_notifications:
        data = {'notification': notif, 'transaction': None, 'book': None}
        if notif.related_transaction_id:
            # Fetch the transaction and its associated book
            transaction = Transaction.query.options(
                db.joinedload(Transaction.book) # Eager load the book
            ).get(notif.related_transaction_id)

            if transaction:
                data['transaction'] = transaction
                data['book'] = transaction.book # Access the loaded book

        notifications_data.append(data)

    # Optionally mark all as read upon viewing the page
    # Or implement a "Mark as Read" button per notification or for all
    # for item in notifications_data:
    #     if not item['notification'].is_read:
    #         item['notification'].is_read = True
    # try:
    #    db.session.commit()
    # except Exception as e:
    #    db.session.rollback()
    #    app.logger.error(f"Error marking notifications as read for user {current_user.id}: {e}")

    return render_template('notifications.html', title="Notifications", notifications_data=notifications_data)

# --- Route to Mark a single Notification as Read (using JS potentially, or a simple POST) ---
@app.route('/notification/mark_read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first_or_404()
    if not notification.is_read:
        notification.is_read = True
        try:
            db.session.commit()
            # Return success (e.g., for AJAX call) or redirect back
            flash('Notification marked as read.', 'success') # Optional feedback
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error marking notification {notification_id} as read: {e}")
            flash('Error marking notification as read.', 'danger')
    # Redirect back to notifications or wherever the user came from
    return redirect(request.referrer or url_for('notifications'))


# --- Transaction Action Routes (Accept, Reject, Complete, Cancel) ---

@app.route('/transaction/accept/<int:transaction_id>', methods=['POST'])
@login_required
def accept_transaction(transaction_id):
    # Eager load related data
    transaction = Transaction.query.options(
        db.joinedload(Transaction.book),
        db.joinedload(Transaction.requester)
    ).get_or_404(transaction_id)
    book = transaction.book
    requester = transaction.requester

    # Authorization: Only the book owner can accept
    if transaction.owner_id != current_user.id:
        app.logger.warning(f"Unauthorized accept attempt on transaction {transaction_id} by user {current_user.id}")
        abort(403)

    # State check
    if transaction.status != 'pending' or book.status != 'pending':
         flash('This request cannot be accepted at this time (status is not pending).', 'warning')
         return redirect(url_for('notifications'))

    # --- Get and Validate Contact Info from Form ---
    submitted_contact_info = request.form.get('contact_info', '').strip()
    if not submitted_contact_info:
        flash('Please provide the contact information you wish to share with the requester.', 'danger')
        # Pass necessary data back if rendering the same template, but redirect is simpler here
        return redirect(url_for('notifications'))
        # Optional: Add more validation (e.g., length, basic format check)
    # --- End Validation ---

    # --- Update Transaction, Store Contact Info, Create Notification ---
    transaction.status = 'accepted'
    transaction.action_timestamp = datetime.utcnow()
    transaction.seller_contact_info = submitted_contact_info # <<< SAVE aSUBMITTED INFO
    db.session.add(transaction) # Add updated transaction to session

    # Book status remains 'pending' until completion

    # Create notification for the REQUESTER with the SUBMITTED contact info
    requester_message = (
        f"Good news! Your request for '{book.title}' has been accepted "
        f"by {current_user.username}. Please contact them using the details provided: "
        f"<strong>{submitted_contact_info}</strong>" # <<< USE SUBMITTED INFO
    )

    requester_notification = Notification(
        user_id=transaction.requester_id,
        message=requester_message,
        related_transaction_id=transaction.id
    )
    db.session.add(requester_notification)

    try:
        db.session.commit()
        flash('Request accepted! The requester has been notified with the contact details you provided.', 'success')
    except Exception as e:
        db.session.rollback()
        # Reset status if commit failed? Or just show error?
        # transaction.status = 'pending' # Revert status
        # db.session.commit() # Try to save revert
        flash(f'Error accepting request: {str(e)}', 'danger')
        app.logger.error(f"Error accepting transaction {transaction_id}: {e}")

    return redirect(url_for('notifications'))


@app.route('/transaction/reject/<int:transaction_id>', methods=['POST'])
@login_required
def reject_transaction(transaction_id):
    transaction = Transaction.query.options(db.joinedload(Transaction.book)).get_or_404(transaction_id)
    book = transaction.book

    # Authorization: Only the book owner can reject
    if transaction.owner_id != current_user.id:
        abort(403)

    # State check
    if transaction.status != 'pending' or book.status != 'pending':
         flash('This request cannot be rejected at this time (status is not pending).', 'warning')
         return redirect(url_for('notifications'))

    # --- Update Transaction, Reset Book Status, Notify Requester ---
    transaction.status = 'rejected'
    transaction.action_timestamp = datetime.utcnow()
    book.status = 'available' # Make book available again
    db.session.add(transaction)
    db.session.add(book)

    # Create notification for the requester
    requester_message = f"Unfortunately, your request for '{book.title}' was rejected by the owner."
    requester_notification = Notification(
        user_id=transaction.requester_id,
        message=requester_message,
        related_transaction_id=transaction.id
    )
    db.session.add(requester_notification)

    try:
        db.session.commit()
        flash('Request rejected. The book is available again and the requester has been notified.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Error rejecting request: {str(e)}', 'danger')
        app.logger.error(f"Error rejecting transaction {transaction_id}: {e}")
        # Rollback status changes if commit failed
        book.status = 'pending' # Or original status before this attempt
        db.session.commit() # Try to commit status revert

    return redirect(url_for('notifications'))


@app.route('/transaction/complete/<int:transaction_id>', methods=['POST'])
@login_required
def complete_transaction(transaction_id):
    transaction = Transaction.query.options(db.joinedload(Transaction.book)).get_or_404(transaction_id)
    book = transaction.book

    # Authorization: Only the book owner can mark as complete
    if transaction.owner_id != current_user.id:
        abort(403)

    # State check: Must be 'accepted'
    if transaction.status != 'accepted':
        flash('This transaction cannot be marked as complete yet (it was not accepted).', 'warning')
        return redirect(url_for('notifications'))

    # --- Update Transaction, Update Book Status, Cancel Others ---
    transaction.status = 'completed'
    transaction.completion_timestamp = datetime.utcnow()
    # In complete_transaction route, after transaction.status = 'completed'
    if transaction.transaction_type == 'donation':
        book.status = 'donated'
    else: # 'sale'
        book.status = 'sold'
        db.session.add(book) # Final state for the book
        db.session.add(transaction)

    # Notify Requester (optional, but good)
    requester_message = f"The transaction for '{book.title}' has been marked as complete by the owner. Enjoy the book!"
    requester_notification = Notification(
        user_id=transaction.requester_id,
        message=requester_message,
        related_transaction_id=transaction.id
    )
    db.session.add(requester_notification)

    # Cancel other PENDING requests for the same book and notify those requesters
    other_pending_transactions = Transaction.query.filter(
        Transaction.book_id == book.id,
        Transaction.id != transaction.id,
        Transaction.status == 'pending'
    ).all()

    for other_trans in other_pending_transactions:
        other_trans.status = 'cancelled' # A specific status for auto-cancellation
        db.session.add(other_trans)
        # Notify the other requesters
        cancel_msg = f"The book '{book.title}' you requested is no longer available as a transaction has been completed."
        cancel_notification = Notification(
            user_id=other_trans.requester_id,
            message=cancel_msg,
            related_transaction_id=other_trans.id
        )
        db.session.add(cancel_notification)

    try:
        db.session.commit()
        flash(f"Transaction for '{book.title}' marked as complete! The book is now marked as sold/donated.", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error completing transaction: {str(e)}', 'danger')
        app.logger.error(f"Error completing transaction {transaction_id}: {e}")
        # Consider reverting status if commit fails? Complex recovery.

    return redirect(url_for('notifications')) # Or redirect to owner's dashboard/book list

# Optional: Allow requester to cancel their PENDING request
@app.route('/transaction/cancel/<int:transaction_id>', methods=['POST'])
@login_required
def cancel_transaction(transaction_id):
    transaction = Transaction.query.options(db.joinedload(Transaction.book)).get_or_404(transaction_id)
    book = transaction.book

    # Authorization: Only the requester can cancel their own request
    if transaction.requester_id != current_user.id:
        abort(403)

    # State check: Must be 'pending'
    if transaction.status != 'pending':
        flash('This request cannot be cancelled at this time (it is not pending).', 'warning')
        return redirect(url_for('notifications')) # Or user's request history page

    # --- Update Transaction, Reset Book Status, Notify Owner ---
    transaction.status = 'cancelled'
    transaction.action_timestamp = datetime.utcnow() # Mark when it was cancelled
    book.status = 'available' # Make book available again
    db.session.add(transaction)
    db.session.add(book)

    # Notify the owner
    owner_message = f"{current_user.username} has cancelled their request for your book: '{book.title}'. The book is available again."
    owner_notification = Notification(
        user_id=transaction.owner_id,
        message=owner_message,
        related_transaction_id=transaction.id
    )
    db.session.add(owner_notification)

    try:
        db.session.commit()
        flash('Your request has been cancelled.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error cancelling request: {str(e)}', 'danger')
        app.logger.error(f"Error cancelling transaction {transaction_id} by user {current_user.id}: {e}")
        # Revert status if commit fails
        book.status = 'pending'
        db.session.commit() # Try commit revert

    return redirect(url_for('notifications')) # Or user's request history

# ... (other imports and app setup) ...

# ... (your existing routes) ...

@app.route('/past_books')
@login_required # Or remove login_required if it's a public log, but usually for users
def past_books():
    # Query for books that are 'sold' or where a 'donation' transaction was 'completed'.
    # We also need the transaction details to see who the requester was.

    # Option 1: Query completed transactions and get their books
    # This is generally better if you want to show who received the book.
    completed_transactions = Transaction.query.filter(
        Transaction.status == 'completed' # Or specific statuses for completed sales/donations
    ).options(
        db.joinedload(Transaction.book).joinedload(Book.owner), # Eager load book and its owner
        db.joinedload(Transaction.requester) # Eager load requester
    ).order_by(Transaction.completion_timestamp.desc()).all()

    # Prepare data for the template
    past_book_data = []
    for trans in completed_transactions:
        if trans.book: # Ensure book exists
            past_book_data.append({
                'title': trans.book.title,
                'author': trans.book.author,
                'original_owner_username': trans.book.owner.username,
                'requester_username': trans.requester.username if trans.requester else "N/A",
                'transaction_type': trans.transaction_type.capitalize(), # 'Sale' or 'Donation'
                'completed_date': trans.completion_timestamp,
                'book_id': trans.book.id # For a potential link
            })

    # Option 2: Query books with status 'sold' or 'donated'
    # This is simpler if you only care about the book and its original owner,
    # but might not directly give you the recipient unless you link back to transactions.
    # sold_or_donated_books = Book.query.filter(
    #     or_(Book.status == 'sold', Book.status == 'donated') # Adjust statuses as needed
    # ).options(
    #     db.joinedload(Book.owner) # Eager load owner
    # ).order_by(Book.date_posted.desc()).all() # Or order by a completion date if you add one to Book model

    return render_template('past_books.html',
                           title='Past Books',
                           transactions=past_book_data) # or books=sold_or_donated_books for option 2


@app.errorhandler(404)
def page_not_found(e):
    # Your existing code is fine
    return render_template('404.html', title='Page Not Found'), 404

@app.errorhandler(500)
def internal_server_error(e):
    # Your existing code is fine
     db.session.rollback()
     app.logger.error(f"Server Error: {e}", exc_info=True)
     return render_template('500.html', title='Server Error'), 500

# --- Main Execution Block (Keep as is, remove db.create_all if using Migrate exclusively) ---
if __name__ == '__main__':
    # Remove this block if you ONLY use flask db commands for schema management
    # with app.app_context():
    #    db.create_all() # Creates tables based on models if they don't exist
    #    print("Database tables checked/created.")

    import logging
    logging.basicConfig(level=logging.INFO)
    # if app.debug: # Configure logging level based on debug status
    #     logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    # else:
    #     logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

    app.run(debug=True)

# Remove the print statement below if no longer needed for CLI debugging
# print("--- app.py loaded successfully for CLI ---")