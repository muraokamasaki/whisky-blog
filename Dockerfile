FROM python:3.7-alpine

RUN adduser -D whisky

WORKDIR /home/whisky

COPY requirements.txt requirements.txt
RUN python -m venv venv
RUN venv/bin/pip install -r requirements.txt
RUN venv/bin/pip install gunicorn 'PyMySQL<0.9'

COPY app app
COPY migrations migrations
COPY whisky.py config.py boot.sh ./
RUN chmod +x boot.sh

ENV FLASK_APP whisky.py

RUN chown -R whisky:whisky ./
USER whisky

EXPOSE 5000
ENTRYPOINT ["./boot.sh"]