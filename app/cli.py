import os

import click

from app import Config


def register(app):
    @app.cli.group()
    def translate():
        """Translation and localization commands"""
        pass

    @translate.command()
    @click.argument('lang')
    def init(lang):
        """Initialize a new language. Creates a new po file for that language.

        USAGE in command line:
            $ flask translate init LANG

        param:
            LANG - 2 letter language code for the language to be added (with optional country code)

        examples:
            $ flask translate init en
            $ flask translate init en-us
        """
        lang = lang.lower()
        if lang not in Config.LANGUAGES:
            Config.LANGUAGES.append(lang)
            if os.system('pybabel extract -F babel.cfg -k _l -o messages.pot .'):
                raise RuntimeError('extract command failed.')
            if os.system('pybabel init -i messages.pot -d app/translations -l' + lang):
                raise RuntimeError('inti command failed.')
            os.remove('messages.pot')

        else:
            raise RuntimeError('Language already added to application.')

    @translate.command()
    def update():
        """Update the po files for all languages.

        USAGE in command line:
            $ flask translate update
        """
        if os.system('pybabel extract -F babel.cfg -k _l -o messages.pot .'):
            raise RuntimeError('extract command failed')
        if os.system('pybabel update -i messages.pot -d app/translations'):
            raise RuntimeError('update command failed')
        os.remove('messages.pot')

    @translate.command()
    def compile():
        """Compile all languages.

        USAGE in command line:
            $ flask translate compile
        """
        if os.system('pybabel compile -d app/translations'):
            raise RuntimeError('compile command failed')
