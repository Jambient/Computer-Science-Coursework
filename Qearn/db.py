from flaskext.mysql import MySQL
from flask import Flask, current_app, g
from pymysql import cursors

mysql = MySQL(autocommit=True, cursorclass=cursors.DictCursor)

def get_db():
    if 'db' not in g:
        g.db = mysql.connect().cursor()
    
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_app(app):
    mysql.init_app(app)
    app.teardown_appcontext(close_db)