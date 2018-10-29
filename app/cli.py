import os;


def register(app):
    @app.cli.group()
    def translate():
        """Translation and localization commands"""
        pass

    @translate.command()
    def compile():
        """Compile languages"""
        if os.system('pybabel compile -d app/translations'):
            raise RuntimeError('compile command failed')