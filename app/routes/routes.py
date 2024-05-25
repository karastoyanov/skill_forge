import re, secrets, os
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.exceptions import Unauthorized
# Import the mail functions
from app.mailtrap import send_reset_email, send_welcome_mail
# Import the database instance
from app.database.db_init import db
# Import the forms and models
from app.forms import LoginForm, RegistrationForm, PasswordResetForm
from app.models import User, ResetToken
# Import MongoDB transactions functions
from app.database.mongodb_transactions import session_transaction, user_register_transaction

bp = Blueprint('main', __name__)

# Get the directory of the current script
base_dir = os.path.dirname(os.path.abspath(__file__))

########### Routes handling user login/logout and registration ###########
# Define routes for login and register pages
@bp.route('/', methods=['GET', 'POST'])
def login():
    # Import the bcrypt instance
    from app import bcrypt
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter((User.username==form.username.data) | (User.email==form.username.data)).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, force=True)
            session_transaction('userLogins', user.user_id, user.username, datetime.now())
            return redirect(url_for('main.main_page'))
        else:
            flash('Login unsuccessful. Please check your username and password.', 'error')
    return render_template('index.html', form=form)

# Route to handle the logout functionality
@bp.route('/logout')
@login_required
def logout():
    session_transaction('userLogouts', current_user.user_id, current_user.username, datetime.now())
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('main.login'))

# Handle the registration route
@bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if the email or username is already in use
        existing_user = User.query.filter((User.email == form.email.data) | (User.username == form.username.data)).first()
        if existing_user:
            flash('Email or username already in use', 'error')
            return redirect(url_for('main.register'))
        # Create a new user
        # Import the bcrypt instance
        from app import bcrypt
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(email=form.email.data, username=form.username.data, 
                        first_name=form.first_name.data, last_name=form.last_name.data, 
                        password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        send_welcome_mail(form.email.data, form.username.data)
        user_register_transaction('userRegister', new_user.user_id, new_user.username, datetime.now())
        flash('Your account has been created! You are now able to log in.', 'success ')
        return redirect(url_for('main.login'))
    return render_template('register.html', form=form)

# Custom error handler for Unauthorized (401) error
@bp.errorhandler(401)
def unauthorized_error(error):
    # Redirect users to a specific page and flash a error message
    flash('You must be logged in to access this page.', 'error')
    return redirect(url_for('main.login'))

########### Routes handling password reset functionality ###########
# Route to open the forgot password form
@bp.route('/forgot_password')
def open_forgot_password():
    return render_template('forgot_password.html')

@bp.route('/reset_password/<user_id>/<username>/<token>/<expiration_time>', methods=['GET', 'POST'])
def open_reset_password(token, user_id, username, expiration_time):
    form = PasswordResetForm(
        user_id=user_id,
        username=username,
        token=token,
        expiration_time=expiration_time
    )
    return render_template('reset_password.html', token=token, user_id=user_id, username=username, expiration_time=expiration_time, form=form)

@bp.route('/send_email_token', methods=['POST'])
def send_email_token():
    email = request.form.get('email_address')
    if len(email) == 0:
        flash('Please provide an email address.', 'error')
        return redirect(url_for('main.open_forgot_password'))
    
    user_mail = request.form.get('email_address')
    current_user = User.query.filter_by(email=user_mail).first()
    if current_user:
        user_id = User.query.filter_by(email=email).first().user_id
        username = User.query.filter_by(email=email).first().username
        # Generate a unique token
        token = secrets.token_urlsafe(32)
        # Calculate expiration time (60 minutes from now)
        expiration_time = datetime.now() + timedelta(minutes=60)
        new_token = ResetToken(user_id=user_id, username=username, user_email=user_mail, token=token, expiration_time=expiration_time)
        db.session.add(new_token)
        db.session.commit()

        # Send email with reset link containing the token
        send_reset_email(token, username, email, expiration_time)
        return redirect(url_for('main.open_reset_password', token=token, user_id=user_id, username=username, expiration_time=expiration_time))
    flash('User with this email does not exist.', 'error')
    return redirect(url_for('main.open_forgot_password'))

@bp.route('/save_new_password', methods=['POST'])
def update_new_password():
    form = PasswordResetForm()

    if form.validate_on_submit():
        user_id = form.user_id.data
        username = form.username.data
        token = form.token.data
        user_token = form.user_token.data
        new_password = form.new_password.data
        expiration_time = form.expiration_time.data

        if user_token is None or user_token != token:
            flash('Invalid token.', 'error')
            return redirect(url_for('main.open_reset_password', token=token, user_id=user_id, username=username, expiration_time=expiration_time))

        if datetime.now().strftime("%Y-%m-%d %H:%M:%S") > expiration_time:
            flash('Token has expired.', 'error')
            return redirect(url_for('main.open_reset_password', token=token, user_id=user_id, username=username, expiration_time=expiration_time))

        user = User.query.get(user_id)
        from app import bcrypt
        user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        used_token = ResetToken.query.filter_by(user_id=user_id, token=user_token).first()
        db.session.delete(used_token)
        db.session.commit()
        flash(f'Password for {username} successfully changed. Now you can log in with your new password.', 'success')
        return redirect(url_for('main.login'))  # Redirect to the login page after successful password reset

    # Print and Flash errors if form validation fails
    if form.errors:
        print("Form Errors:", form.errors)

    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form, field).label.text} - {error}", 'error')

    # Pass necessary parameters to the template in case of errors
    return render_template('reset_password.html', form=form, token=form.token.data, user_id=form.user_id.data, username=form.username.data, expiration_time=form.expiration_time.data)

########### Routes handling main apge ###########
# Open the main page
@bp.route('/home')
@login_required
def main_page():
    title_path = os.path.join(base_dir, '../main_page_title')
    info_path = os.path.join(base_dir, '../main_page_info')
    try:
        with open(title_path, 'r') as file:
            title_content = file.read().strip()
    except FileNotFoundError:
        title_content = "Default Title"
    try:
        with open(info_path, 'r') as file:
            content = file.read().strip()
    except FileNotFoundError:
        content = "Default Content"
        
    server_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return render_template('homepage.html', server_time=server_time, title_content=title_content, content=content)