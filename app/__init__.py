import os
import logging
from logging.handlers import SMTPHandler, RotatingFileHandler

from elasticsearch import Elasticsearch
from flask import Flask, session, request, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_moment import Moment
from flask_babel import Babel
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView


from config import Config


# Turn off autoflush to let review editing to be saved in session.dirty
db = SQLAlchemy(session_options={"autoflush": False})
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
mail = Mail()
moment = Moment()
babel = Babel()
admin = Admin()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    babel.init_app(app)
    admin.init_app(app)
    app.elasticsearch = Elasticsearch([app.config['ELASTICSEARCH_URL']]) if app.config['ELASTICSEARCH_URL'] else None

    from app.errors.handlers import bp as errors_bp
    app.register_blueprint(errors_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    if not app.debug and not app.testing:
        if app.config['MAIL_SERVER']:
            auth = None
            if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
                auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            secure = None
            if app.config['MAIL_USE_TLS']:
                secure = ()
            mail_handler = SMTPHandler(
                mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
                fromaddr='no-reply@' + app.config['MAIL_SERVER'],
                toaddrs=app.config['ADMINS'], subject='Whisky Blog failure',
                credentials=auth, secure=secure)
            mail_handler.setLevel(logging.ERROR)
            app.logger.addHandler(mail_handler)
        if app.config['LOG_TO_STDOUT']:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.INFO)
            app.logger.addHandler(stream_handler)
        else:
            if not os.path.exists('logs'):
                os.mkdir('logs')
            file_handler = RotatingFileHandler('logs/WhiskyBlog.logs', maxBytes=10240, backupCount=10)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Whisky Blog startup')

        register_tags(app)

    register_admins(app)

    return app


@babel.localeselector
def get_locale():
    try:
        language = session['language']
    except KeyError:
        language = None
    if language is not None:
        return language
    return request.accept_languages.best_match(current_app.config['LANGUAGES'])


from app import models


def register_tags(app):
    from app import db
    from app.models import Tag
    from app.main.info import all_tags

    with app.app_context():
        for t in all_tags:
            if Tag.query.filter_by(name=t[0]).first() is None:
                db.session.add(Tag(name=t[0]))

        db.session.commit()


def register_admins(app):
    from flask_login import current_user
    from app import db
    from app.models import User, Review, Tag

    class BaseModelView(ModelView):
        def is_accessible(self):
            return current_user.is_authenticated and current_user.id == 1

    class UserView(BaseModelView):
        column_exclude_list = ['password_hash']
        can_create = False
        can_edit = True

    class ReviewView(BaseModelView):
        can_create = False
        can_edit = False

    admin.add_view(UserView(User, db.session))
    admin.add_view(ReviewView(Review, db.session))
    admin.add_view(BaseModelView(Tag, db.session))
