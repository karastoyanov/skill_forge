import random, string, base64, json, os
from datetime import datetime
from flask import Blueprint, redirect, url_for, request, render_template, jsonify, flash, abort, send_file
from flask_login import login_required, current_user
# Import the forms and models
from app.models import Guild
from app.forms import CreateGuildForm
# Import code runners
from app.code_runners import run_python, run_javascript, run_java, run_csharp
# Import the database instance
from app.database.db_init import db
from sqlalchemy.orm import joinedload
# Import MongoDB transactions functions
from app.database.mongodb_transactions import mongo_transaction
# Import admin_required decorator
from app.user_permission import admin_required
import io
import base64

bp_guild = Blueprint('guilds', __name__)

# Redirect to create new guild page
@bp_guild.route('/create_guild', methods=['GET'])
def open_create_guild():
    form = CreateGuildForm()
    return render_template('guild_templates/create_guild.html', form=form)

# Redirect to the guilds list page
@bp_guild.route('/guilds', methods=['GET'])
def open_guilds_list():
    guilds = Guild.query.all()
    return render_template('guild_templates/guilds_list.html', guilds=guilds)

# Handle the guild avatar image requests
@bp_guild.route('/guilds/avatar/<guild_id>')
def get_guild_avatar(guild_id):
    guild = Guild.query.filter_by(guild_id=guild_id).first_or_404()
    if guild.guild_avatar:
        img_data = guild.guild_avatar
    else:
        # Return a default image if no avatar is set
        with open('app/static/images/default-guild-avatar.png', 'rb') as f:
            img_data = f.read()
    return send_file(io.BytesIO(img_data), mimetype='image/jpeg')

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