import base64, json, random, string, io
from datetime import datetime
from bson import ObjectId
from flask import Blueprint, redirect, url_for, request, flash, render_template, abort, send_file, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.orm import joinedload
# Import the forms and models
from app.models import SubmitedSolution, User, UserAchievement, Quest, ReportedQuest, SubmitedQuest, Achievement
from app.forms import QuestForm, UserProfileForm, GiveAchievementForm
# Import the database instance
from app.database.db_init import db
# Import MongoDB transactions functions
from app.database.mongodb_transactions import mongo_transaction
from app.database.mongodb_init import mongo1_db, mongo1_client


# Import admin_required decorator
from app.user_permission import admin_required

bp_usr = Blueprint('usr', __name__)

fields_flash_messages = {
    'about_me': 'About me',
    'first_name': 'First name',
    'last_name': 'Last name',
    'email': 'Email',
    'facebook_profile': 'Facebook profile',
    'instagram_profile': 'Instagram profile',
    'github_profile': 'GitHub profile',
    'discord_id': 'Discord ID',
    'linked_in': 'LinkedIn',
    'avatar': 'Avatar'
}

#  Open the user profile page
@bp_usr.route('/my_profile', methods=['GET', 'POST'])
@login_required
def open_user_profile():
    form = UserProfileForm()
    user_id = current_user.user_id
    user = User.query.get(user_id)

    if form.validate_on_submit():
        new_email = form.email.data.lower()
        current_email = user.email.lower()
        if new_email != current_email:
            is_email_taken = User.query.filter(func.lower(User.email) == new_email).first()
            if is_email_taken:
                flash('This email is already taken. Please choose another one.', 'danger')
                return redirect(url_for('usr.open_user_profile'))
            
        if 'submit' in request.form:
            try:
                user.about_me = form.about_me.data
                user.first_name = form.first_name.data
                user.last_name = form.last_name.data
                user.email = form.email.data
                user.facebook_profile = form.facebook_profile.data
                user.instagram_profile = form.instagram_profile.data
                user.github_profile = form.github_profile.data
                user.discord_id = form.discord_id.data
                user.linked_in = form.linked_in.data

                db.session.commit()

                mongo_transaction(
                    'user_info_update',
                    action=f'User {user.username} updated their info',
                    user_id=user_id,
                    username=user.username,
                    timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
                flash('Profile updated successfully', 'success')
                return redirect(url_for('usr.open_user_profile'))
            except Exception as e:
                flash(f'Error during updating user\'s profile!', 'danger')
                return redirect(url_for('usr.open_user_profile'))
            
            
        if 'update_avatar' in request.form:
            if form.avatar.data:
                avatar_data = form.avatar.data.read()
                user.avatar = avatar_data
                db.session.commit()
                flash('Avatar updated successfully', 'success')
            else:
                flash('Please select an avatar to upload', 'warning')
            return redirect(url_for('usr.open_user_profile'))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{fields_flash_messages[field]}: {error}', 'danger')
                return redirect(url_for('usr.open_user_profile'))

    if request.method == 'GET':
        form.about_me.data = user.about_me
        form.first_name.data = user.first_name
        form.last_name.data = user.last_name
        form.email.data = user.email
        form.facebook_profile.data = user.facebook_profile
        form.instagram_profile.data = user.instagram_profile
        form.github_profile.data = user.github_profile
        form.discord_id.data = user.discord_id
        form.linked_in.data = user.linked_in

    user_submited_quests = SubmitedQuest.query.filter(SubmitedQuest.quest_author_id == user_id).all()
    user_solved_quests = SubmitedSolution.query.options(
        joinedload(SubmitedSolution.coding_quest)
    ).filter_by(user_id=user_id).all()    
    user_achievements = UserAchievement.query.filter(UserAchievement.user_id == user_id).all()
    avatar_base64 = base64.b64encode(user.avatar).decode('utf-8') if user.avatar else None
    user_status = user.user_online_status
    last_logged_date = user.last_status_update

    with open('app/static/configs/levels.json', 'r') as file:
        levels_data = json.load(file)

    current_level_xp = 0  # Default for level 1 or the lowest rank
    max_xp = 0

    # Loop through levels to find the user's current level and next level max XP
    for level in levels_data:
        for rank, data in level.items():
            if rank == user.rank:
                max_xp = data['max_xp']  # Get max XP for the next level
                break
            else:
                current_level_xp = data['max_xp']  # Set current level's XP as the max of the previous level

    # Calculate XP percentage for the progress bar
    xp_percentage = int(((user.xp - current_level_xp) / (max_xp - current_level_xp)) * 100)


    return render_template('user_profile.html',
                        form=form,
                        user=user,
                        user_submited_quests=user_submited_quests,
                        user_solved_quests=user_solved_quests,
                        user_achievements=user_achievements,
                        avatar_base64=avatar_base64,
                        user_status=user_status,
                        last_logged_date=last_logged_date,
                        xp_percentage=xp_percentage,
                        max_xp=max_xp)


# Get the users avatar
@bp_usr.route('/avatar/<user_id>', methods=['GET'])
def get_user_avatar(user_id):
    user = User.query.filter_by(user_id=user_id).first_or_404()
    if user.avatar:
        img_data = user.avatar
    else:
        with open('app/static/images/anvil.png', 'rb') as f:
            img_data = f.read()
    return send_file(io.BytesIO(img_data), mimetype='image/jpeg')

# Open user for editing from the Admin Panel
@bp_usr.route('/edit_user/<user_id>', methods=['GET'])
@login_required
@admin_required
def open_edit_user(user_id):
    form = GiveAchievementForm()

    # Retrieve the specific user from the database, based on the user_id
    user = User.query.get(user_id)
    achievements = Achievement.query.all()
    # Dynamically populate the achievement field with (id, name-description) pairs
    form.achievement.choices = [(achievement.achievement_id, f'{achievement.achievement_name} - {achievement.achievement_description}') for achievement in achievements]
    return render_template('edit_user.html', user=user, achievements=achievements, form=form)

# Handle user edit from the Admin Panel
@bp_usr.route('/edit_user_db', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user_db():
    user_id = request.form.get('user_id')
    user_role = request.form.get('user_role')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('user_email')

    user = User.query.get(user_id)
    
    # Updating information about the user
    user.user_role = user_role
    user.first_name = first_name
    user.last_name = last_name
    user.email = email
    db.session.commit()
    return redirect(url_for('usr.open_admin_panel'))

# Give user an achievement from the Admin panel
@bp_usr.route('/give_achievement/<user_id>', methods=['POST'])
@login_required
@admin_required
def give_achievement(user_id):
    form = GiveAchievementForm()
    
    user = User.query.get_or_404(user_id)
    achievements = Achievement.query.all()

    # Dynamically populate the achievement field with (id, name-description) pairs
    form.achievement.choices = [
        (achievement.achievement_id, f'{achievement.achievement_name} - {achievement.achievement_description}')
        for achievement in achievements
    ]

    if form.validate_on_submit():
        achievement_id = form.achievement.data  # Get the selected achievement_id from form
        achievement = Achievement.query.get(achievement_id)
        
        user_achievement_exist = UserAchievement.query.filter_by(user_id=user_id, achievement_id=achievement_id).first()
        if user_achievement_exist:
            flash(f'{user.username} already has the achievement "{achievement.achievement_name}".', 'error')
            return render_template('edit_user.html', user=user, achievements=achievements, form=form)

        if achievement:
            user_achievement_id = f"USR-ACHV-{''.join(random.choices(string.digits, k=16))}"
            # Ensure the user_achievement_id is unique
            while UserAchievement.query.filter_by(user_achievement_id=user_achievement_id).first():
                user_achievement_id = f"USR-ACHV-{''.join(random.choices(string.digits, k=16))}"
            
            # Create new UserAchievement entry
            user_achievement = UserAchievement(
                user_achievement_id=user_achievement_id,
                user_id=user_id,
                username=user.username,
                achievement_id=achievement.achievement_id,
                earned_on=datetime.now()
            )
            
            db.session.add(user_achievement)
            db.session.commit()
            
            flash(f'Achievement "{achievement.achievement_name}" given successfully to {user.username}.', 'success')
            return render_template('edit_user.html', user=user, achievements=achievements, form=form)

    # If not a POST request or form is invalid, render the form again
    flash('Invalid form data. Please try again.', 'error')
    return render_template('edit_user.html', user=user, achievements=achievements, form=form)



# Route to handle the user profile (self-open)
@bp_usr.route('/user_profile/<username>', methods=['GET'])
@login_required
def open_user_profile_view(username):
    # Get the user info from the database
    user = User.query.filter_by(username=username).first()
    if not user:
        return abort(404)
    user_id = user.user_id
    if user_id == current_user.user_id:
        return redirect(url_for('usr.open_user_profile'))
    else:
        # Convert avatar binary data to Base64-encoded string
        avatar_base64 = base64.b64encode(user.avatar).decode('utf-8') if user.avatar else None
        
        # Get the last logged date
        user_status = User.query.filter(User.user_id == user_id).first().user_online_status
        last_logged_date = User.query.filter(User.user_id == user_id).first().last_status_update
        
        # Get the xp points for the level rank
        with open('app/static/configs/levels.json', 'r') as file:
            levels_data = json.load(file)
        current_level_xp = 0  # Default for level 1 or the lowest rank
        max_xp = 0
        # Loop through levels to find the user's current level and next level max XP
        for level in levels_data:
            for rank, data in level.items():
                if rank == user.rank:
                    max_xp = data['max_xp']  # Get max XP for the next level
                    break
                else:
                    current_level_xp = data['max_xp']  # Set current level's XP as the max of the previous level

        # Calculate XP percentage for the progress bar
        xp_percentage = int(((user.xp - current_level_xp) / (max_xp - current_level_xp)) * 100)
        
        # Get the user achievements
        user_achievements = UserAchievement.query.filter(UserAchievement.user_id == user_id).all()
        
        if user:
            return render_template('user_profile_view.html', 
                                user=user, 
                                avatar=avatar_base64,
                                user_status=user_status,
                                user_achievements=user_achievements,
                                last_logged_date=last_logged_date,
                                max_xp=max_xp,
                                xp_percentage=xp_percentage)
        else:
            # Handle the case where the user is not found
            return abort(404)

# Redirect to the Admin Panel (Admin Role in the database is needed)
@bp_usr.route('/admin_panel', methods=['GET'])
@login_required
@admin_required
def open_admin_panel():
    create_quest_post = QuestForm()
    # Retrieve all quests from the database
    all_quests = Quest.query.all()
    all_submited_quests = SubmitedQuest.query.all()
    # Get the User ID for the session
    logged_user_id = current_user.user_id
    # Get the user object with the User ID from the session
    currently_logged_user = User.query.get(logged_user_id)
    # Get all reported quests
    all_reported_quests = ReportedQuest.query.all()
    # Get all users (this is needed so we can extract the name of the user who has reported a quest)
    all_users = User.query.all()
    # Get all admins (this is needed so we can create a dropdown menu in the `Check Reports` table)
    
    # Take all JSON files from skill_forge_logs collection in MongoDB
    # Start a client session
    
    # Function to convert ObjectId to string
    def convert_objectid_to_string(submission):
        # Create a new dict with string IDs
        submission['_id'] = str(submission['_id'])
        return submission
    
    with mongo1_client.start_session() as session:
        with session.start_transaction():
            try:
                db = mongo1_client['skill_forge_logs']
                python_submissions = list(db['python_submissions']
                                        .find({}, session=session)
                                        .sort('timestamp', -1)
                                        .limit(20))
                
                java_submissions = list(db['java_submissions']
                                        .find({}, session=session)
                                        .sort('timestamp', -1)
                                        .limit(20))
                
                csharp_submissions = list(db['csharp_submissions']
                                        .find({}, session=session)
                                        .sort('timestamp', -1)
                                        .limit(20))
                
                javascript_submissions = list(db['javascript_submissions']
                                            .find({}, session=session)
                                            .sort('timestamp', -1)
                                            .limit(20))
                
                # Convert ObjectId in each submission to string
                python_submissions = [convert_objectid_to_string(sub) for sub in python_submissions]
                java_submissions = [convert_objectid_to_string(sub) for sub in java_submissions]
                csharp_submissions = [convert_objectid_to_string(sub) for sub in csharp_submissions]
                javascript_submissions = [convert_objectid_to_string(sub) for sub in javascript_submissions]

                all_submissions = python_submissions + java_submissions + csharp_submissions + javascript_submissions
            except Exception as e:
                session.abort_transaction()
                all_submissions = {}
                flash('An error occurred while fetching the submissions.', 'error')
                return redirect(url_for('usr.open_admin_panel'))
    
    all_admins = User.query.filter_by(user_role='Admin').all()
    if currently_logged_user.user_role == "Admin":
        return render_template('admin_panel.html', 
        all_quests=all_quests, 
        all_submited_quests=all_submited_quests, 
        reported_quests=all_reported_quests,
        all_users=all_users,
        all_admins=all_admins,
        form=create_quest_post,
        all_submissions=all_submissions)
    flash('You must be an admin to access this page.', 'error')
    return redirect(url_for('main.login'))

@bp_usr.route('/submissions_logs/<submission_id>', methods=['GET'])
@login_required
@admin_required
def submission_log(submission_id):
    with mongo1_client.start_session() as session:
        with session.start_transaction():
            try:
                db = mongo1_client['skill_forge_logs']
                collections = ['python_submissions', 'java_submissions', 'csharp_submissions', 'javascript_submissions']

                submission = None

                for collection in collections:
                    submission = db[collection].find_one({'submission_id': submission_id})
                    if submission:
                        break
                
                # Convert ObjectId and datetime fields to strings
                if isinstance(submission['_id'], ObjectId):
                    submission['_id'] = str(submission['_id'])
                if isinstance(submission['timestamp'], datetime):
                    submission['timestamp'] = submission['timestamp'].isoformat()
                submission_json = json.dumps(submission, indent=4)
                quest = Quest.query.get(submission['quest_id'])
            except Exception as e:
                session.abort_transaction()
                submission = {}
                quest = {}
                flash(f'An error occurred while fetching the submission. {e}', 'error')
                return redirect(url_for('usr.open_admin_panel'))
    return render_template('display_submission_log.html', submission=submission_json, quest=quest)

# Ban user route
@bp_usr.route('/ban_user/<user_id>', methods=['POST'])
@login_required
@admin_required
def ban_user(user_id, ban_reason='no reason'):
    # Retrieve the specific user from the database, based on the user_id
    user = User.query.get(user_id)
    request_arguments = dict(request.args) # This prints {'ban_reason': 'some_value'}
    # Set new values to these three fields in the database
    user.is_banned = True
    user.ban_date = datetime.now()
    user.ban_reason = request_arguments['ban_reason']
    db.session.commit()
    return redirect(url_for('usr.open_admin_panel'))

# Unban user route
@bp_usr.route('/unban_user/<user_id>', methods=['POST'])
@login_required
@admin_required
def unban_user(user_id):
    # Retrieve the specific user from the database, based on the user_id
    user = User.query.get(user_id)
    # Set new values to these three fields in the database
    user.is_banned = False
    user.ban_date = None
    user.ban_reason = ''
    db.session.commit()
    return redirect(url_for('usr.open_admin_panel'))