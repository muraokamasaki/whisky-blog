# Whisky Blog - Heroku

This is the whisky-blog version specifically for deployment on Heroku.
Can be accessed [here](http://whisky-blog.herokuapp.com/)

## Heroku add-ons

- Heroku Postgres
- Searchbox Elasticsearch

## Differences from master

- Added Heroku specific files:
    - Procfile
    - runtime.txt

- Added dependencies in requirements.txt
    - certifi
    - elasticsearch 6.x
    - psycopg2-binary
    
- Changed search functions to use Elasticsearch 6.x (originally Elasticsearch 7.x)
    - Searchbox only supports up to Elasticsearch 6.x