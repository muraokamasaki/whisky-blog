from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, SelectField,\
    SelectMultipleField, IntegerField
from wtforms.validators import DataRequired, ValidationError, Length, NumberRange
from app.models import User, Distillery, Whisky


all_tags = [('Fresh Fruit', 'Fresh Fruit'), ('Dried Fruit', 'Dried Fruit'), ('Citrus', 'Citrus'), ('Floral', 'Floral'),
            ('Honey', 'Honey'), ('Spicy', 'Spicy'), ('Woody', 'Woody'),  ('Vanilla', 'Vanilla'), ('Coffee', 'Coffee'),
            ('Sherry', 'Sherry'), ('Wine', 'Wine'), ('Chocolate', 'Chocolate'), ('Malty', 'Malty'), ('Nutty', 'Nutty'),
            ('Leather', 'Leather'), ('Grass', 'Grass'), ('Salty', 'Salty'), ('Smoke', 'Smoke'), ('Peat', 'Peat'),
            ('Medicinal', 'Medicinal')]

locations = [('Speyside', 'Speyside'), ('Highlands', 'Highlands'), ('Lowlands', 'Lowlands'), ('Islay', 'Islay'),
             ('Islands', 'Islands'), ('Campbeltown', 'Campbeltown'), ('Irish', 'Irish'), ('Japanese', 'Japanese'),
             ('Bourbon', 'Bourbon'), ('Others', 'Others')]


class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    about_me = TextAreaField('About Me', validators=[Length(min=0, max=140)])
    submit = SubmitField('Submit')

    def __init__(self, original_username, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError('Please use a different username')


class ReviewForm(FlaskForm):
    nose = TextAreaField('Nose', validators=[DataRequired(), Length(min=0, max=255)])
    palate = TextAreaField('Palate', validators=[DataRequired(), Length(min=0, max=255)])
    finish = TextAreaField('Finish', validators=[DataRequired(), Length(min=0, max=255)])
    score = IntegerField('Score (out of 100)', validators=[DataRequired(), NumberRange(min=0, max=100)])
    add_tags = SelectMultipleField('Tags', choices=all_tags)
    submit = SubmitField('Submit')


class AddDistilleryForm(FlaskForm):
    name = StringField('Distillery', validators=[DataRequired()])
    region = SelectField('Region', choices=locations)
    submit = SubmitField('Add a distillery')

    def validate_name(self, name):
        distillery = Distillery.query.filter_by(name=name.data.title()).first()
        if distillery is not None:
            raise ValidationError('Distillery has already been added')


class AddWhiskyForm(FlaskForm):
    name = StringField('Name / Age statement', validators=[DataRequired()])
    about = TextAreaField('About Whisky (optional)', validators=[Length(min=0, max=255)])
    submit = SubmitField('Add a whisky')

    def __init__(self, **kwargs):
        self.distillery = kwargs['distillery']
        super(AddWhiskyForm, self).__init__(**kwargs)

    def validate_name(self, name):
        whisky = Whisky.query.filter_by(distillery_id=self.distillery.id).filter_by(name=name.data).first()
        if whisky is not None:
            raise ValidationError('Whisky has already been added')


class EditDistilleryForm(FlaskForm):
    name = StringField('Distillery', validators=[DataRequired()])
    region = SelectField('Region', choices=locations)
    submit = SubmitField('Edit distillery info')

    def __init__(self, original_name, *args, **kwargs):
        super(EditDistilleryForm, self).__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        if name.data != self.original_name:
            distillery = Distillery.query.filter_by(name=name.data).first()
            if distillery is not None:
                raise ValidationError('There is already a distillery with that name')


class EditWhiskyForm(FlaskForm):
    name = StringField('Name / Age statement', validators=[DataRequired()])
    about = TextAreaField('About Whisky (optional)', validators=[Length(min=0, max=255)])
    submit = SubmitField('Edit whisky info')

    def __init__(self, *args, **kwargs):
        super(EditWhiskyForm, self).__init__(*args, **kwargs)
        self.original_name = kwargs['name']
        self.distillery = kwargs['distillery']

    def validate_name(self, name):
        if name.data != self.original_name:
            whisky = Whisky.query.filter_by(distillery_id=self.distillery.id).filter_by(name=name.data).first()
            if whisky is not None:
                raise ValidationError('There is already a whisky with that name')
