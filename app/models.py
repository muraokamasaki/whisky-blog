from datetime import datetime
from hashlib import md5
from time import time

import jwt
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

from app import db, login
from app.search import add_doc_to_index, remove_doc_from_index, query_index


tags = db.Table('tags',
                db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True),
                db.Column('review_id', db.Integer, db.ForeignKey('review.id'), primary_key=True))

whiskies_listed = db.Table('whiskies_listed',
                           db.Column('whisky_id', db.Integer, db.ForeignKey('whisky.id'), primary_key=True),
                           db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True))


class SearchableMixin:
    """Wrapper for query_document that converts the list of ids into a sqlalchemy query object in the same order."""
    @classmethod
    def search(cls, expr, excluded, page, per_page):
        ids, total = query_index(cls.__tablename__, expr, excluded, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0
        # append to when in the order that is returned by elasticsearch
        when = []
        for i, v in enumerate(ids):
            when.append((v, i))
        return cls.query.filter(cls.id.in_(ids)).order_by(db.case(when, value=cls.id)), total

    """Saves all changes to be committed in _changes in the db session before actually committing."""
    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': [obj for obj in session.new if isinstance(obj, cls)],
            'update': [obj for obj in session.dirty if isinstance(obj, cls)],
            'delete': [obj for obj in session.deleted if isinstance(obj, cls)]
        }

    """Updates the elasticsearch index with all changes that were committed."""
    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            add_doc_to_index(cls.__tablename__, obj)
        for obj in session._changes['update']:
            add_doc_to_index(cls.__tablename__, obj)
        for obj in session._changes['delete']:
            remove_doc_from_index(cls.__tablename__, obj)
        session._changes = None

    """Refreshes an index with objects from the database"""
    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_doc_to_index(cls.__tablename__, obj)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    about_me = db.Column(db.String(140))
    reviews = db.relationship('Review', backref='author', lazy='dynamic')
    whiskies_listed = db.relationship('Whisky', secondary=whiskies_listed, lazy='dynamic',
                                      backref=db.backref('users', lazy='dynamic'))

    def __repr__(self):
        return f'<{type(self).__name__}(id={self.id}, username={self.username})>'

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
        return not self.reviews.filter_by(whisky_id=id).first()

    def get_whiskies_listed(self):
        return self.whiskies_listed.all()

    def add_whisky(self, wsk):
        if not self.has_whisky(wsk):
            self.whiskies_listed.append(wsk)

    def remove_whisky(self, wsk):
        if self.has_whisky(wsk):
            self.whiskies_listed.remove(wsk)

    def has_whisky(self, wsk):
        return self.whiskies_listed.filter(Whisky.id == wsk.id).count() > 0

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)


@login.user_loader
def load_user(id_num):
    return User.query.get(int(id_num))


class Review(SearchableMixin, db.Model):
    searchable_fields = ['nose', 'palate', 'finish']
    id = db.Column(db.Integer, primary_key=True)
    nose = db.Column(db.String(255))
    palate = db.Column(db.String(255))
    finish = db.Column(db.String(255))
    score = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    whisky_id = db.Column(db.Integer, db.ForeignKey('whisky.id'))
    tags = db.relationship('Tag', secondary=tags, lazy='dynamic',
                           backref=db.backref('reviews', lazy='dynamic'))

    def __repr__(self):
        return f'<{type(self).__name__}(id={self.id})>'

    def get_tags(self):
        return self.tags.all()

    def add_tag(self, tag):
        if not self.is_tagged(tag):
            self.tags.append(tag)

    def remove_tag(self, tag):
        if self.is_tagged(tag):
            self.tags.remove(tag)

    def is_tagged(self, tag):
        return self.tags.filter(Tag.id == tag.id).count() > 0


db.event.listen(db.session, 'before_commit', Review.before_commit)
db.event.listen(db.session, 'after_commit', Review.after_commit)


class Whisky(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    about = db.Column(db.String(255))
    distillery_id = db.Column(db.Integer, db.ForeignKey('distillery.id'))
    reviews = db.relationship('Review', backref='whisky', lazy='dynamic')

    def __repr__(self):
        return f'<{type(self).__name__}(id={self.id}, distillery={self.distillery.name}, name={self.name})>'

    def number_reviews(self):
        return self.reviews.count() if not None else 0

    def get_users(self):
        return self.users.all()


class Distillery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    location = db.Column(db.String(64), index=True)
    owner = db.Column(db.String(64))
    founded = db.Column(db.Integer)
    whiskys = db.relationship('Whisky', backref='distillery', lazy='dynamic')

    def __repr__(self):
        return f'<{type(self).__name__}(id={self.id}, name={self.name})>'

    def has_whiskies(self):
        return self.whiskys.count() if not None else 0


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)

    def __repr__(self):
        return f'<{type(self).__name__}(id={self.id}, name={self.name})>'

    def get_reviews(self):
        return self.reviews.all()
