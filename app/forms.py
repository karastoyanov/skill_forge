from flask_wtf import FlaskForm
from flask import flash
from wtforms import StringField, PasswordField, SubmitField, HiddenField, SelectField, TextAreaField, RadioField, FileField, BooleanField
from wtforms.validators import Email, Length, EqualTo, DataRequired, ValidationError, Regexp, Optional
import re


def validate_password(form, password):
    errors = []
    if not re.search(r'[A-Z]', password.data):
        flash('Password must contain at least one uppercase letter', 'error')
        errors.append('Password must contain at least one uppercase letter')
    
    if len(password.data) < 10:
        flash('Password must be at least 10 characters long', 'error')
        errors.append('Password must be at least 10 characters long')

    if not re.search(r'\d', password.data):
        flash('Password must contain at least one digit', 'error')
        errors.append('Password must contain at least one digit')

    if not re.search(r'[!@#$%^&*()_+=\-{}\[\]:;,<.>?]', password.data):
        flash('Password must contain at least one special character', 'error')
        errors.append('Password must contain at least one special character')
    
    if form.confirm.data != password.data:
        flash('Passwords must match', 'error')
        errors.append('Passwords must match')
    
    if errors:
        raise ValidationError(errors)
    
    return password

# Custom validator for email field, requires email to contain only Latin characters
def latin_characters_only(form, field):
    latin_chars_regex = re.compile(r'^[a-zA-Z0-9@._+-]+$')
    if not latin_chars_regex.match(field.data):
        raise ValidationError('Email must contain only Latin characters.')

########### Login Form ###########
class LoginForm(FlaskForm):
    username = StringField('Username', [DataRequired()])
    password = PasswordField('Password', [DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

########### Register Form ###########
class RegistrationForm(FlaskForm):
    username = StringField('', render_kw={'placeholder': 'Username'}, validators=[DataRequired(), Length(min=4, max=25)])
    first_name = StringField('', render_kw={'placeholder': 'First name'}, validators=[DataRequired(), Length(min=1, max=30)])
    last_name = StringField('', render_kw={'placeholder': 'Last name'}, validators=[DataRequired(), Length(min=1, max=30)])
    email = StringField('', render_kw={'placeholder': 'Email address'}, validators=[DataRequired(), Email(), latin_characters_only])   
    password = PasswordField('', validators=[
        DataRequired(),
        Length(min=10, max=50, message='Password must be between 10 and 50 characters.'),
        Regexp(re.compile(r'.*[A-Z].*'), message='Password must contain at least one uppercase letter.'),
        Regexp(re.compile(r'.*[0-9].*'), message='Password must contain at least one digit.'),
        Regexp(re.compile(r'.*[!@#$%^&*()_+=\-{}\[\]:;,<.>?].*'), message='Password must contain at least one special character.')
    ],
        render_kw={'placeholder': 'Password'})
    confirm = PasswordField('', render_kw={'placeholder': 'Repeat password'}, validators=[
        DataRequired(), 
        EqualTo('password', message='Passwords must match'), 
        Length(min=10, max=50, message='Password must be between 10 and 50 characters.')
    ])
    submit = SubmitField('Register')
    
########### Contact Form ###########
class ContactForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email address', validators=[DataRequired(), Email(), latin_characters_only])
    subject = StringField('Subject', validators=[DataRequired()])
    message = TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Send Message')

########### Password Reset Request Form ###########
class EmailResetForm(FlaskForm):
    email_address = StringField('Email Address', validators=[DataRequired(), Email(), latin_characters_only])
    submit = SubmitField('Send Me Token')

########### Password Reset Form ###########
class PasswordResetForm(FlaskForm):
    token = HiddenField('Token', validators=[DataRequired()])
    user_id = HiddenField('User ID', validators=[DataRequired()])
    username = HiddenField('Username', validators=[DataRequired()])
    expiration_time = HiddenField('Expiration Time', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=10, message='Password must be at least 10 characters long.'),
        Regexp(re.compile(r'.*[A-Z].*'), message='Password must contain at least one uppercase letter.'),
        Regexp(re.compile(r'.*[0-9].*'), message='Password must contain at least one digit.'),
        Regexp(re.compile(r'.*[!@#$%^&*()_+=\-{}\[\]:;,<.>?].*'), message='Password must contain at least one special character.')
    ],
    render_kw={'placeholder': 'New Password'})
    confirm_password = PasswordField('Repeat Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Passwords must match')
    ],
    render_kw={'placeholder': 'Repeat Password'})
    submit = SubmitField('Reset Password')

########### Create New Quest Form - as Admin ###########
class QuestForm(FlaskForm):
    quest_name = StringField(
        'Quest Name', 
        validators=[DataRequired(), Length(max=100)], 
        render_kw={'id': ""}
    )
    quest_language = SelectField(
        'Quest Language', 
        choices=[('Python', 'Python'), ('JavaScript', 'JavaScript'), ('Java', 'Java'), ('C#', 'C#')], 
        validators=[DataRequired()], 
        render_kw={"id": ""}
    )
    quest_difficulty = SelectField(
        'Quest Difficulty', 
        choices=[('Novice Quests', 'Novice Quests'), ('Adventurous Challenges', 'Adventurous Challenges'), ('Epic Campaigns', 'Epic Campaigns')], 
        validators=[DataRequired()],
        render_kw={"id": ""}
    )
    quest_condition = TextAreaField(
        'Quest Condition', 
        validators=[DataRequired()],
        render_kw={"id": ""}
    )
    quest_inputs = TextAreaField(
        'Inputs Samples', 
        validators=[DataRequired()],
        render_kw={"id": ""}
    )
    quest_outputs = TextAreaField(
        'Outputs Samples', 
        validators=[DataRequired()],
        render_kw={"id": ""}
    )
    function_template = TextAreaField(
        'Quest Template', 
        validators=[DataRequired()],
        render_kw={"id": ""}
    )
    quest_unitests = TextAreaField(
        'Quest Unit Tests - Not Obligatory'
    )
    submit = SubmitField('Submit Quest')
    
########### Edit Quest Form - as Admin ###########
########### Edit Submited Quest - as Admin ###########
########### Edit Submited Quest - as Regular User ###########
class EditQuestForm(FlaskForm):
    quest_id = HiddenField('Quest ID')
    quest_name = StringField('Quest Name', validators=[DataRequired()])
    quest_language = SelectField('Quest Language', choices=[('Python', 'Python'), ('JavaScript', 'JavaScript'), ('Java', 'Java'), ('C#', 'C#')], validators=[DataRequired()])
    quest_difficulty = SelectField('Quest Difficulty', choices=[('Novice Quests', 'Novice Quests'), ('Adventurous Challenges', 'Adventurous Challenges'), ('Epic Campaigns', 'Epic Campaigns')], validators=[DataRequired()])
    quest_condition = TextAreaField('Quest Condition', validators=[DataRequired()])
    function_template = TextAreaField('Quest Template', validators=[DataRequired()])
    quest_test_inputs = TextAreaField('Quest Tests Inputs', validators=[DataRequired()], render_kw={'rows': 10})
    quest_test_outputs = TextAreaField('Quest Tests Outputs', validators=[DataRequired()], render_kw={'rows': 10})
    quest_unitests = TextAreaField('Quest Unit Tests')
    submit = SubmitField('Save Changes')

########### Edit Reported Quest Form - as Admin ###########
class EditReportedQuestForm(FlaskForm):
    quest_id = HiddenField('Quest ID')
    quest_name = StringField('Quest Name', validators=[DataRequired()])
    quest_language = SelectField('Quest Language', choices=[('Python', 'Python'), ('JavaScript', 'JavaScript'), ('Java', 'Java'), ('C#', 'C#')], validators=[DataRequired()])
    quest_difficulty = SelectField('Quest Difficulty', choices=[('Novice Quests', 'Novice Quests'), ('Adventurous Challenges', 'Adventurous Challenges'), ('Epic Campaigns', 'Epic Campaigns')], validators=[DataRequired()])
    quest_condition = TextAreaField('Quest Condition', validators=[DataRequired()])
    function_template = TextAreaField('Quest Template', validators=[DataRequired()])
    quest_test_inputs = TextAreaField('Quest Tests Inputs', validators=[DataRequired()])
    quest_test_outputs = TextAreaField('Quest Tests Outputs', validators=[DataRequired()])
    quest_unitests = TextAreaField('Quest Unit Tests')
    progress_option = RadioField('Progress Option', choices=[('In Progress', 'In Progress'), ('Resolved', 'Resolved')])
    submit = SubmitField('Save Changes')
    
########### Publish New Comment On Quest Form ###########
class PublishCommentForm(FlaskForm):
    comment = TextAreaField('Comment', validators=[DataRequired(), Length(max=1000)])
    submit = SubmitField('Comment')

########### Contact Form ###########
class ContactForm(FlaskForm):
    username = StringField('Name', validators=[DataRequired(), Length(min=4, max=25)],)
    email = StringField('Email address', validators=[DataRequired(), Email(), latin_characters_only])
    subject = StringField('Subject', validators=[DataRequired(), Length(min=4, max=25)])
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=10)])
    submit = SubmitField('Send Message')
    
########### User Profile Form - update user's profile ###########
class UserProfileForm(FlaskForm):
    about_me = TextAreaField('About Me', validators=[Optional()])
    first_name = StringField('First Name', validators=[Optional()])
    last_name = StringField('Last Name', validators=[Optional()])
    email = StringField('Email', validators=[Optional(), Email(), latin_characters_only])
    facebook_profile = StringField('Facebook Profile', validators=[Optional()])
    instagram_profile = StringField('Instagram', validators=[Optional()])
    github_profile = StringField('GitHub', validators=[Optional()])
    discord_id = StringField('Discord ID', validators=[Optional()])
    linked_in = StringField('LinkedIn', validators=[Optional()])
    avatar = FileField('Upload Avatar', name="update_avatar", validators=[Optional()])
    submit = SubmitField('Update Profile', name="submit")

########### Submit Quest Form - as a Regular User ###########
class QuestSubmissionForm(FlaskForm):
    quest_name = StringField('Quest Name', validators=[DataRequired(), Length(max=100)])
    quest_language = SelectField('Quest Language', choices=[('Python', 'Python'), ('JavaScript', 'JavaScript'), 
                                                            ('Java', 'Java'), 
                                                            ('C#', 'C#')], 
                                 validators=[DataRequired()])
    quest_difficulty = SelectField('Quest Difficulty', choices=[('Novice Quests', 'Novice Quests'), 
                                                                ('Adventurous Challenges', 'Adventurous Challenges'), 
                                                                ('Epic Campaigns', 'Epic Campaigns'), ('Abyssal Trials', 'Abyssal Trials')], 
                                   validators=[DataRequired()])
    quest_condition = TextAreaField('Quest Condition', validators=[DataRequired()])
    function_template = TextAreaField('Example Solution', validators=[Optional()])
    quest_inputs = TextAreaField('Inputs Samples', validators=[DataRequired()])
    quest_outputs = TextAreaField('Outputs Samples', validators=[DataRequired()])
    quest_unitests = TextAreaField('Quest Unit Tests')
    submit = SubmitField('Submit Quest')

########### Manage Submited Quest - as an Admin ###########
class QuestApprovalForm(FlaskForm):
    submited_quest_id = HiddenField()
    submited_quest_name = StringField('Quest Name', validators=[DataRequired()])
    submited_quest_author = HiddenField('Quest Author', validators=[DataRequired()])
    submited_quest_date_added = HiddenField('Quest Date Added', validators=[DataRequired()])
    submited_quest_language = SelectField('Quest Language', choices=[('Python', 'Python'), ('JavaScript', 'JavaScript'), ('Java', 'Java'), ('C#', 'C#')], validators=[DataRequired()])
    submited_quest_difficulty = SelectField('Quest Difficulty', choices=[('Novice Quests', 'Novice Quests'), ('Adventurous Challenges', 'Adventurous Challenges'), ('Epic Campaigns', 'Epic Campaigns')], validators=[DataRequired()])
    submited_quest_condition = TextAreaField('Quest Condition', validators=[DataRequired()])
    submited_function_template = TextAreaField('Quest Template', validators=[DataRequired()])
    submited_quest_unitests = TextAreaField('Quest Unit Tests', validators=[Optional()])
    submited_quest_inputs = TextAreaField('Quest Test Inputs', validators=[DataRequired()])
    submited_quest_outputs = TextAreaField('Quest Test Outputs', validators=[DataRequired()])
    request_changes_comment = TextAreaField('Request Changes Comment', validators=[Optional()], 
                                            render_kw={'placeholder': 'Provide a comment for the author'})
    action = HiddenField()
    approve = SubmitField('Approve Quest', render_kw={'value': 'approve'})
    request_changes = SubmitField('Request Changes', render_kw={'value': 'request-changes'})
    reject = SubmitField('Reject Quest', render_kw={'value': 'reject'})
    save_changes = SubmitField('Save Changes', render_kw={'value': 'save-changes'})
    
########### Create New Guild Form ###########
class CreateGuildForm(FlaskForm):
    name = StringField('Guild Name', validators=[DataRequired(), Length(min=5, max=50)])
    description = TextAreaField('Description', validators=[Optional(), Length(min=10, max=500)])
    avatar = FileField('Avatar')
    submit = SubmitField('Create Guild')
    
########### Edit Guild Form ###########

########### Invite User to Guild Form - As Guild Master ###########
class InviteUserForm(FlaskForm):
    user_input = StringField('User', validators=[DataRequired(message="Please provide a username or user ID")])
    message = TextAreaField('Message (optional)', validators=[Optional(), Length(min=10, max=200)])
    submit = SubmitField('Send Invite')