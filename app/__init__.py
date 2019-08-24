import os
import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
import pprint

from elasticsearch import Elasticsearch
from flask import Flask, session, request, current_app, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_mail import Mail
from flask_moment import Moment
from flask_babel import Babel
from flask_admin import Admin, BaseView, expose
from flask_admin.contrib.sqla import ModelView


from config import Config
from app.search import get_mappings, insert_mapping, delete_mapping


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

    return app


# Looks for the language the current flask app is set to.
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


"""Create custom admin views for `User`, `Review` and `Tag` models"""


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


class TagView(BaseModelView):
    @expose('/bulk/')
    def bulk_view(self):
        from app.main.info import all_tags
        for t in all_tags:
            tag = self.model.query.filter_by(name=t[0]).first()
            if not tag:
                self.session.add(self.model(name=t[0]))
        self.session.commit()
        return redirect('/admin/tag')


class SearchView(BaseView):
    @expose('/')
    def index(self):
        maps = get_mappings()
        return self.render('admin/search.html', mapping=pprint.pformat(maps))

    @expose('/insert/')
    def insert(self):
        # insert elasticsearch mapping
        insert_mapping('review')
        return redirect('/admin/search')

    @expose('/delete/')
    def delete(self):
        # delete elasticsearch mapping
        delete_mapping('review')
        return redirect('/admin/search')

    def is_accessible(self):
        return current_user.is_authenticated and current_user.id == 1


admin.add_view(UserView(models.User, db.session))
admin.add_view(ReviewView(models.Review, db.session))
admin.add_view(TagView(models.Tag, db.session))
admin.add_view(SearchView(name='Search', endpoint='search'))

