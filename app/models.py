import jwt
from datetime import datetime
from hashlib import md5
from time import time
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login


tags = db.Table('tags',
                db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True),
                db.Column('review_id', db.Integer, db.ForeignKey('review.id'), primary_key=True))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    reviews = db.relationship('Review', backref='author', lazy='dynamic')
    about_me = db.Column(db.String(140))

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(digest, size)

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode({'reset_password': self.id, 'exp': time() + expires_in},
                          current_app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')

    def not_commented(self, id):
        try:
            return not self.reviews.filter_by(whisky_id=id).first_or_404()
        except:
            return True

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    whisky_id = db.Column(db.Integer, db.ForeignKey('whisky.id'))
    tags = db.relationship('Tag', secondary=tags, lazy='dynamic',
                           backref=db.backref('reviews', lazy='dynamic'))

    def __repr__(self):
        return '<Review {}>'.format(self.body)

    def add_tag(self, tag):
        if not self.is_tagged(tag):
            self.tags.append(tag)

    def remove_tag(self, tag):
        if self.is_tagged(tag):
            self.tags.remove(tag)

    def is_tagged(self, tag):
        return self.tags.filter(Tag.id == tag.id).count() > 0


class Whisky(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    about = db.Column(db.String(255))
    distillery_id = db.Column(db.Integer, db.ForeignKey('distillery.id'))
    reviews = db.relationship('Review', backref='whisky', lazy='dynamic')

    def __repr__(self):
        return '<{0} {1}>'.format(self.distillery.name, self.name)

    def number_reviews(self):
        return self.reviews.count() if not None else 0


class Distillery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    location = db.Column(db.String(64), index=True)
    whiskys = db.relationship('Whisky', backref='distillery', lazy='dynamic')

    def __repr__(self):
        return '<Distillery {}>'.format(self.name)


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)

    def __repr__(self):
        return '<Tag {}>'.format(self.name)
