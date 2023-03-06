from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from Qearn.auth import login_required
from Qearn.db import get_db

bp = Blueprint('dashboard', __name__)

@bp.route('/')
def dashboard():
    if g.user:
        return redirect(url_for('dashboard.home'))
    else:
        return render_template('index.html')

@bp.route('/home')
@login_required
def home():
    return render_template('dashboard/home.html')

@bp.route('/classes')
@login_required
def classes():
    ## get users classrooms
    db = get_db()
    db.execute('SELECT ID, SchoolID, ClassName, ClassGroup FROM class as c, `user-to-class` as u WHERE (u.ClassID = c.ID) AND (u.UserID = %s)', (g.user['ID'],))
    classes = db.fetchall()

    for classroom in classes:
        # get member count
        db.execute('SELECT COUNT(UserID) as UserCount FROM `user-to-class` WHERE ClassID = %s', (classroom['ID'],))
        member_count = db.fetchone()
        classroom['MemberCount'] = member_count['UserCount']


    print(classes)

    return render_template('dashboard/classes.html', classes=classes)

@bp.route('/classes/<int:classID>')
@login_required
def single_class(classID):
    db = get_db()

    ## check user can access this classroom
    db.execute('SELECT CASE WHEN EXISTS (SELECT * FROM `user-to-class` WHERE UserID = %s AND ClassID = %s) THEN 1 ELSE 0 END AS Result', (g.user['ID'], classID))
    isInClass = db.fetchone()
    
    if isInClass['Result'] == 0:
        return redirect('/classes')

    ## get data about this classroom
    db.execute('SELECT ID, SchoolID, ClassName, ClassGroup FROM class WHERE ID = %s', (classID,))
    classData = db.fetchone()

    return render_template('dashboard/single_class.html', classData=classData)

@bp.route('/settings')
@login_required
def settings():
    return render_template('dashboard/settings.html')