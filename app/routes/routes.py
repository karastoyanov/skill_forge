import secrets, os, base64
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
# Import the mail functions
from app.mailtrap import send_reset_email, send_welcome_mail, send_contact_email
# Import the database instance
from app.database.db_init import db
from app import bcrypt
# Import the forms and models
from app.forms import LoginForm, RegistrationForm, EmailResetForm, PasswordResetForm, ContactForm
from app.models import User, ResetToken, Quest, SubmitedSolution
# Import MongoDB transactions functions
from app.database.mongodb_transactions import mongo_transaction

bp = Blueprint('main', __name__)

# Get the directory of the current script
base_dir = os.path.dirname(os.path.abspath(__file__))

########### Routes handling user login/logout and registration ###########
# Define routes for login and register pages
@bp.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter((User.username==form.username.data) | (User.email==form.username.data)).first()
        if user:
            if not user.is_banned:
                if bcrypt.check_password_hash(user.password, form.password.data):
                    login_user(user, remember=form.remember_me.data)
                    print(form.remember_me.data)
                    user.user_online_status = "Online"
                    user.last_status_update = datetime.now()
                    db.session.commit()
                    mongo_transaction('user_logins', action=f"User {user.username} logged in", user_id=user.user_id, username=user.username, timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    return redirect(url_for('main.main_page'))
                else:
                    flash('Login unsuccessful. Please check your username and password.', 'error')
            else:
                flash('Your account has been banned. Please contact the administrator.', 'error')
        else:
            flash('Login unsuccessful. Please check your username and password.', 'error')
    return render_template('index.html', form=form)

# Route to handle the logout functionality
@bp.route('/logout')
@login_required
def logout():
    user = current_user
    user.user_online_status = "Offline"
    user.last_status_update = datetime.now()
    db.session.commit()
    mongo_transaction('user_logouts', action=f'User {user.username} logged out', user_id=user.user_id, username=user.username, timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
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
            return render_template('register.html', form=form)
        # Create a new user
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(email=form.email.data, username=form.username.data, 
                        first_name=form.first_name.data, last_name=form.last_name.data, 
                        password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        send_welcome_mail(form.email.data, form.username.data)
        flash('Your account has been created! You are now able to log in.', 'success')
        return render_template('index.html', form=LoginForm())
    else:
        if form.errors:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"{getattr(form, field).label.text} - {error}", 'error')
    return render_template('register.html', form=form)


########### Routes handling password reset functionality ###########
# Route to open the forgot password form
@bp.route('/forgot_password')
def open_forgot_password():
    form = EmailResetForm()
    return render_template('forgot_password.html', form=form)

@bp.route('/send_email_token', methods=['POST'])
def send_email_token():
    form = EmailResetForm()
    if form.validate_on_submit():
        email = form.email_address.data
        current_user = User.query.filter_by(email=email).first()
        all_token = ResetToken.query.filter_by(user_email=email).first()
        
        if all_token:
            flash('A password reset link has already been sent to your email. Please check your inbox.', 'error')
            return redirect(url_for('main.login'))
                
        if current_user:
            user_id = current_user.user_id
            username = current_user.username
            # Generate a unique token
            token = secrets.token_urlsafe(32)
            # Calculate expiration time (60 minutes from now)
            expiration_time = datetime.now() + timedelta(minutes=60)
            # Convert expiration_time to string in a format that can be easily parsed later
            expiration_time_str = expiration_time.strftime("%Y-%m-%d %H:%M:%S")
            new_token = ResetToken(user_id=user_id, username=username, user_email=email, token=token, expiration_time=expiration_time_str)
            db.session.add(new_token)
            db.session.commit()

            reset_url = url_for('main.open_reset_password', token=token, user_id=user_id, username=username, expiration_time=expiration_time_str, _external=True)
            # Send email with reset link containing the token
            send_reset_email(reset_url, username, email, expiration_time)
            flash('A password reset link has been sent to your email.', 'success')
            return redirect(url_for('main.login'))
        else:
            flash('User with this email does not exist.', 'error')
            return redirect(url_for('main.open_forgot_password'))

    flash('Invalid email address', 'error')
    return render_template('forgot_password.html', form=form)


@bp.route('/reset_password/', methods=['GET', 'POST'])
def open_reset_password():
    token = request.args.get('token')
    user_id = request.args.get('user_id')
    username = request.args.get('username')
    expiration_time_str = request.args.get('expiration_time')
    
    # Parse expiration_time_str into datetime object
    expiration_time = datetime.strptime(expiration_time_str, "%Y-%m-%d %H:%M:%S")
    
    form = PasswordResetForm()
    form.token.data = token
    form.user_id.data = user_id
    form.username.data = username
    form.expiration_time.data = expiration_time

    if form.validate_on_submit():
        return update_new_password(form)
    
    for error in form.errors:
        flash(f'{form.errors[error][0]}', 'error')
    return render_template('reset_password.html', form=form, token=token, user_id=user_id, username=username, expiration_time=expiration_time)

@bp.route('/save_new_password', methods=['POST'])
def update_new_password(form=None):
    if not form:
        form = PasswordResetForm()

    if form.validate_on_submit():
        user_id = form.user_id.data
        username = form.username.data
        token = form.token.data
        new_password = form.new_password.data
        expiration_time = datetime.strptime(form.expiration_time.data, "%Y-%m-%d %H:%M:%S")

        reset_token = ResetToken.query.filter_by(user_id=user_id, token=token).first()

        if reset_token is None or reset_token.token != token:
            flash('Invalid token.', 'error')
            return redirect(url_for('main.open_reset_password', token=token, user_id=user_id, username=username, expiration_time=expiration_time))

        if datetime.now() > reset_token.expiration_time:
            flash('Token has expired.', 'error')
            return redirect(url_for('main.open_reset_password', token=token, user_id=user_id, username=username, expiration_time=expiration_time))

        user = User.query.get(user_id)
        from app import bcrypt
        user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        db.session.delete(reset_token)
        db.session.commit()
        mongo_transaction('user_password_reset', action=f'User {username} restored the password', user_id=user_id, username=username, timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
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
    user_count = User.query.count()
    online_users = User.query.filter_by(user_online_status='Online').count()
    online_users_query = User.query.filter_by(user_online_status="Online").all()
    user_guild = current_user.guild_id
    if user_guild:
        guild_avatar_base64 = base64.b64encode(current_user.guild.guild_avatar).decode('utf-8') if current_user.guild.guild_avatar else None
    else:
        guild_avatar_base64 = None
    quest_count = Quest.query.count()
    solutions_count = SubmitedSolution.query.filter_by(quest_passed=True).count()
    server_time = datetime.now()
    return render_template('homepage.html', 
                           server_time=server_time, 
                           user_count=user_count,
                           online_users=online_users,
                           user_guild=user_guild,
                           guild_avatar=guild_avatar_base64,
                           quest_count=quest_count,
                           solutions_count=solutions_count)

# Check the number of online users. Function used by the websockets and client side script.
@bp.route('/get_online_users')
def get_online_users():
    online_users = User.query.filter_by(user_online_status='Online').count()
    return jsonify({'online_users': online_users})

# Route to open the about page
@bp.route('/about')
@login_required
def about():
    return render_template('about.html')

# Route to open the contact page
@bp.route('/contact_us')
@login_required
def contact():
    contact_form = ContactForm()
    username = current_user.username if current_user.is_authenticated else None
    user_email = current_user.email if current_user.is_authenticated else None
    return render_template('contact.html', username=username, user_email=user_email, form=contact_form)

@bp.route('/send_message', methods=['POST'])
@login_required
def send_message():
    contact_form = ContactForm()
    user = contact_form.username.data
    email = contact_form.email.data
    subject = contact_form.subject.data
    message = contact_form.message.data
    if contact_form.validate_on_submit():
        send_contact_email(user, email, subject, message)
        flash('Thank you for contacting us. We will get back to you as soon as possible.', 'success')
        return redirect(url_for('main.contact'))
    flash('Error during sending the email.', 'error')
    for error in contact_form.errors:
        flash(f'{contact_form.errors[error][0]}', 'error')
    return render_template('contact.html', form=contact_form)