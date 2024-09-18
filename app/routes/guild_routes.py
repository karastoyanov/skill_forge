import random, base64, io
from datetime import datetime
from flask import Blueprint, redirect, url_for, request, render_template, jsonify, flash, abort, send_file
from sqlalchemy.sql import or_
from flask_login import login_required, current_user
# Import the forms and models
from app.models import Guild, User, JoinRequest, JoinInvite
from app.forms import CreateGuildForm, InviteUserForm
# Import the database instance
from app.database.db_init import db
# Import MongoDB transactions functions
from app.database.mongodb_transactions import mongo_transaction

bp_guild = Blueprint('guilds', __name__)

# Redirect to create new guild page
@bp_guild.route('/create_guild', methods=['GET'])
@login_required
def open_create_guild():
    form = CreateGuildForm()
    if current_user.guild_id != None:
        flash('You are already a member of a guild!', 'error')
        return render_template('homepage.html')
    return render_template('guild_templates/create_guild.html', form=form)

# Redirect to the guilds list page
@bp_guild.route('/guilds', methods=['GET'])
@login_required
def open_guilds_list():
    guilds = Guild.query.all()
    guild_requests = JoinRequest.query.filter_by(user_id=current_user.user_id, request_status='Pending').all()
    return render_template('guild_templates/guilds_list.html', guilds=guilds, guild_requests=guild_requests)

# Redirect to the guild page
@bp_guild.route('/guilds/<guild_id>', methods=['GET'])
@login_required
def open_guild(guild_id):
    form = InviteUserForm()
  
    guild = Guild.query.filter_by(guild_id=guild_id).first_or_404()
    avatar_base64 = base64.b64encode(guild.guild_avatar).decode('utf-8') if guild.guild_avatar else None
    
    # Get the guild members
    guild_members = guild.members
    guild_members_count = len(guild_members)
    
    # Check if the user is a member of the guild
    if current_user.guild_id != "" or current_user.guild_id != None:
        is_member = current_user.guild_id == guild_id
    else:
        is_member = False
    
    # Check if the user is the guild master
    if current_user.user_id == guild.guild_master_id:
        is_guild_master = True
    else:
        is_guild_master = False
    
    # Get all guild join requests in 'Pending' status
    join_guild_requests = JoinRequest.query.filter_by(guild_id=guild_id, request_status='Pending').all()
    
    return render_template('guild_templates/guild_info.html', 
                           guild=guild, 
                           avatar_base64=avatar_base64, 
                           is_member=is_member,
                           is_guild_master=is_guild_master,
                           join_guild_requests=join_guild_requests,
                           guild_members=guild_members,
                           guild_members_count=guild_members_count,
                           form=form)

# Handle the guild avatar image requests
@bp_guild.route('/guilds/avatar/<guild_id>', methods=['GET'])
@login_required
def get_guild_avatar(guild_id):
    guild = Guild.query.filter_by(guild_id=guild_id).first_or_404()
    if guild.guild_avatar:
        img_data = guild.guild_avatar
    else:
        # Return a default image if no avatar is set
        with open('app/static/images/default-guild-avatar.png', 'rb') as f:
            img_data = f.read()
    return send_file(io.BytesIO(img_data), mimetype='image/jpeg')

# Redirect to the guild info page
@bp_guild.route('/guilds/<guild_id>')
@login_required
def get_guild_info(guild_id):
    guild = Guild.query.filter_by(guild_id=guild_id).first_or_404()
    avatar_base64 = base64.b64encode(User.avatar).decode('utf-8') if guild.guild_avatar else None

    
    return render_template('guild_templates/guild_info.html',
                           guild=guild, 
                           avatar_base64=avatar_base64)

# Join guild send request
@bp_guild.route('/guilds/join_req/<guild_id>')
@login_required
def join_guild(guild_id):
    guild = Guild.query.filter_by(guild_id=guild_id).first_or_404()
    
    existing_request = JoinRequest.query.filter_by(user_id=current_user.user_id, guild_id=guild_id, request_status="Pending").first()
    if existing_request:
        flash('You have already sent a request to join this guild!', 'error')
        return redirect(url_for('guilds.open_guild', guild_id=guild_id))
    
    if current_user.guild_id:
        flash('You are already a member of a guild!', 'error')
        return redirect(url_for('guilds.open_guild', guild_id=guild_id))
    
    request_id = f"JR-{random.randint(1000000, 9999999)}"
    while JoinRequest.query.filter_by(request_id=request_id).first():
        request_id = f"JR-{random.randint(1000000, 9999999)}"
        
    new_request = JoinRequest(
        request_id=request_id,
        user_id=current_user.user_id,
        guild_id=guild_id,
        request_date=datetime.now(),
        request_status='Pending'
    )
    db.session.add(new_request)
    db.session.commit()
    flash('Join guild request sent successfully!', 'success')
    return redirect(url_for('guilds.open_guild', guild_id=guild_id))

# Cancel join guild request
@bp_guild.route('/guilds/cancel_req/<guild_id>')
@login_required
def cancel_request(guild_id):
    guild = Guild.query.filter_by(guild_id=guild_id).first_or_404()
    existing_request = JoinRequest.query.filter_by(user_id=current_user.user_id, guild_id=guild_id, request_status="Pending").first()
    if existing_request:
        existing_request.request_status = 'Cancelled'
        db.session.commit()
        flash('Join guild request cancelled successfully!', 'success')
    else:
        flash('You have not sent a request to join this guild!', 'error')
    # Redirect to the guilds list page
    return redirect(url_for('guilds.open_guilds_list'))

# Invite user to guild - as guild master
@bp_guild.route('/guilds/invite_user/<guild_id>', methods=['GET', 'POST'])
@login_required
def invite_user(guild_id):
    form = InviteUserForm()
    
    if form.validate_on_submit():
        user_input = form.user_input.data
        message = form.message.data
        print(f'User is: {user_input}')
        
        # Query user based on username or user ID
        user = User.query.filter(User.username == user_input).first()
        
        if not user:
            flash('User not found!', 'error')
            return redirect(url_for('guilds.open_guild', guild_id=guild_id))
        
        if user.guild_id is not None and user.guild_id != "":
            flash('User is already a member of a guild!', 'error')
            return redirect(url_for('guilds.open_guild', guild_id=guild_id))
        

        invite_id = f"INV-{random.randint(1000000, 9999999)}"
        while JoinRequest.query.filter_by(request_id=invite_id).first():
            invite_id = f"INV-{random.randint(1000000, 9999999)}"
        
        new_invite = JoinInvite(
            invite_id=invite_id,
            user_id=user.user_id,
            guild_id=guild_id,
            invite_date=datetime.now(),
            invite_status='Pending',
            message=message
        )
        
        db.session.add(new_invite)
        db.session.commit()
        
        flash(f'User {user.username} was invited to join the guild!', 'success')
        return redirect(url_for('guilds.open_guild', guild_id=guild_id, form=form))
    else:
        # Print form errors as flash messages
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in the {getattr(form, field).label.text} field - {error}", 'error')
        return redirect(url_for('guilds.open_guild', guild_id=guild_id))

# Kick user from guild - as guild master
@bp_guild.route('/guilds/kick_user/<user_id>/<guild_id>', methods=['GET', 'POST'])
@login_required
def kick_user(guild_id, user_id):
    guild = Guild.query.filter_by(guild_id=guild_id).first_or_404()
    
    if current_user.user_id != guild.guild_master_id:
        flash('You are not the guild master!', 'error')
        return redirect(url_for('guilds.open_guild', guild_id=guild_id))
    
    if user_id == guild.guild_master_id:
        flash('You cannot kick yourself from the guild!', 'error')
        return redirect(url_for('guilds.open_guild', guild_id=guild_id))
    
    user = User.query.filter_by(user_id=user_id).first_or_404()
    if user.guild_id is None or user.guild_id != guild_id:
        flash('User is not a member of this guild!', 'error')
        return redirect(url_for('guilds.open_guild', guild_id=guild_id))
    
    user.guild_id = None
    guild.guild_members_count -= 1
    db.session.commit()

    flash(f'User {user.username} was kicked from guild successfully!', 'success')
    return redirect(url_for('guilds.open_guild', guild_id=guild_id))

# Leave guild; TODO: logic for masters
@bp_guild.route('/guilds/leave/<user_id>/<guild_id>', methods=['GET', 'POST'])
@login_required
def leave_guild(guild_id, user_id):
    guild = Guild.query.filter_by(guild_id=guild_id).first_or_404()
    user = User.query.filter_by(user_id=user_id).first_or_404()

    if user.guild_id is None or user.guild_id != guild_id:
        flash('You are not a member of this guild!', 'error')
        return redirect(url_for('guilds.open_guild', guild_id=guild_id))

    user.guild_id = None
    guild.guild_members_count -= 1
    db.session.commit()

    flash(f'You just left {guild.guild_name}!', 'success')
    return redirect(url_for('guilds.open_guild', guild_id=guild_id))

# Accept or Decline join guild request - as guild master
@bp_guild.route('/guilds/respond_req/<guild_id>/<request_id>/<action>', methods=['GET', 'POST'])
@login_required
def handle_join_request(request_id, guild_id, action):
    guild = Guild.query.filter_by(guild_id=guild_id).first_or_404()
    # Check if the user is the guild master
    if current_user.user_id != guild.guild_master_id:
        flash('You are not the guild master!', 'error')
        return redirect(url_for('guilds.open_guild', guild_id=guild_id))

    if action == 'accept':
        request = JoinRequest.query.filter_by(request_id=request_id).first_or_404()
        request.request_status = 'Approved'
        db.session.commit()
        new_status = 'Accepted'
        
        # Update the user's guild ID
        user = User.query.filter_by(user_id=request.user_id).first()
        user.guild_id = guild_id
        db.session.commit()

        # Add the user to the guild
        guild.members.append(user)
        db.session.commit()

        # Delete all requests that the user has sent to other guilds
        user_requests = JoinRequest.query.filter_by(user_id=request.user_id, request_status='Pending').all()
        for user_request in user_requests:
            db.session.delete(user_request)
        
        # Delete all invites that has been sent to the user
        user_invites = JoinInvite.query.filter_by(user_id=request.user_id).all()
        for user_invite in user_invites:
            db.session.delete(user_invite)

        db.session.commit()

        flash(f'Request has been {new_status.lower()}! {user.username} is now member of the guild!', 'success')
    elif action == 'decline':
        # Update the request status to 'Rejected'
        request = JoinRequest.query.filter_by(request_id=request_id).first_or_404()
        user = User.query.filter_by(user_id=request.user_id).first()
        request.request_status = 'Rejected'
        db.session.commit()
        new_status = 'Declined'
        flash(f'Request has been {new_status.lower()}! {user.username} was not accepted in the guild!', 'info')

    return redirect(url_for('guilds.open_guild', guild_id=guild_id))

# Create new guild
@bp_guild.route('/guilds/create', methods=['GET', 'POST'])
@login_required
def create_new_guild():
    form = CreateGuildForm()
    if form.validate_on_submit():
        existing_guild = Guild.query.filter_by(guild_name=form.name.data).first()
        if existing_guild:
            flash('This guild name is already taken. Please choose a different name.', 'error')
            return render_template('create_guild.html', form=form)
        
        if form.avatar.data:
            guild_avatar = form.avatar.data.read()
        else:
            with open('app/static/images/default-guild-avatar.png', 'rb') as f:
                guild_avatar = f.read()
    
        # Generate a random guild ID
        while True:
            # Generate a random 7-digit number
            random_digits = random.randint(1000000, 9999999)
            guild_id = f"GD-{random_digits}"
            # Check if this ID already exists in the database
            existing_guild = Guild.query.filter_by(guild_id=guild_id).first()
            if not existing_guild:
                break
        

        # Create new guild
        guild = Guild(
            guild_id=guild_id,
            guild_name=form.name.data,
            description=form.description.data,
            guild_master_id=current_user.user_id,
            guild_avatar=guild_avatar)

        guild.members.append(current_user)
        db.session.add(guild)
        db.session.commit()
        
        mongo_transaction(
            'guild_create',
            action=f'Guild {form.name.data} created by {current_user.username}',
            user_id=current_user.user_id,
            username=current_user.username,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        flash(f'Guild {form.name.data} created successfully!', 'success')
        return redirect(url_for('guilds.create_new_guild'))
    else:
        # Print form errors as flash messages
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in the {getattr(form, field).label.text} field - {error}", 'error')

    return render_template('guild_templates/create_guild.html', form=form)
