from app import create_app, db, cli
from app.models import User, Review, Whisky, Distillery, Tag


app = create_app()
cli.register(app)


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Review': Review, 'Whisky': Whisky, 'Distillery': Distillery, 'Tag': Tag}
