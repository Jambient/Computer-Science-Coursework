from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, session
)
from werkzeug.exceptions import abort

import os, shutil

from Qearn.auth import login_required, load_logged_in_user
from Qearn.db import get_db

from passlib.hash import sha256_crypt

bp = Blueprint('dashboard', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
def get_file_ending(filename):
    ending = filename.rsplit('.', 1)[1].lower()
    return ending
    # return '.' in filename and \
    #        filename.rsplit('.', 1)[1].lower()

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

@bp.route('/classes', methods=('GET', 'POST'))
@login_required
def classes():
    db = get_db()

    if request.method == 'GET':
        ## get users classrooms
        db.execute('SELECT * FROM class as c, `user-to-class` as u WHERE (u.ClassID = c.ID) AND (u.UserID = %s)', (g.user['ID'],))
        classes = db.fetchall()

        for classroom in classes:
            # get member count
            db.execute('SELECT COUNT(UserID) as UserCount FROM `user-to-class` WHERE ClassID = %s', (classroom['ID'],))
            member_count = db.fetchone()
            classroom['MemberCount'] = member_count['UserCount']

    elif request.method == 'POST':
        print('got request')
        
        # check if the post request has the file part
        if 'header-image' not in request.files:
            flash('No file part')

            print('not file sent')
            return redirect(request.url)
        
        file = request.files['header-image']
        fileEnding = get_file_ending(file.filename)

        print('got file with file ending', fileEnding)

        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')

            print('empty file submitted')
            return redirect(request.url)

        if file and fileEnding in ALLOWED_EXTENSIONS:
            ## add new classroom
            db.execute(
                "INSERT INTO class (SchoolID, ClassName, ClassGroup) VALUES (%s, %s, %s)",
                (session['SchoolID'], request.form["name"], request.form["age-group"])
            )
            classId = db.lastrowid
            db.execute(
                "UPDATE class SET HeaderPicture = %s WHERE ID = %s",
                (f'{classId}.{fileEnding}', classId)
            )
            file.save(os.path.join('Qearn/static/classes', f'{classId}.{fileEnding}'))

            ## add teacher to classroom
            db.execute(
                "INSERT INTO `user-to-class` (UserID, ClassID) VALUES (%s, %s)",
                (g.user['ID'], classId)
            )

            return redirect(request.url)
        else:
            print('FILE IS NOT ALLOWED')

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
    db.execute('SELECT * FROM class WHERE ID = %s', (classID,))
    classData = db.fetchone()

    ## get previously played quizzes
    db.execute('SELECT * FROM session, quiz WHERE ClassID = %s ORDER BY DateStarted DESC', (classID))
    previousQuizzes = db.fetchall()
    print(previousQuizzes)

    return render_template('dashboard/single_class.html', classData=classData, quizzes=previousQuizzes)

@bp.route('/classes/<int:classID>/edit')
@login_required
def single_class_edit(classID):
    db = get_db()

    ## check user can access this classroom
    db.execute('SELECT CASE WHEN EXISTS (SELECT * FROM `user-to-class` WHERE UserID = %s AND ClassID = %s) THEN 1 ELSE 0 END AS Result', (g.user['ID'], classID))
    isInClass = db.fetchone()

    ## check user is a teacher
    if g.user['AccountType'] != 'teacher':
        return False

    ## get data about this classroom
    db.execute('SELECT * FROM class WHERE ID = %s', (classID,))
    classData = db.fetchone()

    return render_template('dashboard/single_class_edit.html', classData=classData)

@bp.route('/review')
@login_required
def review():
    db = get_db()

    ## get all the session the user has every run in every classroom
    db.execute('SELECT session.*, quiz.* FROM `user-to-class` as u, session, quiz WHERE u.UserID = %s and session.ClassID = u.ClassID ORDER BY DateStarted DESC', (g.user['ID']),)
    allSessions = db.fetchall()

    for session in allSessions:
        session['onclick'] = f"window.location='review/{session['ID']}'"

    print(allSessions)

    return render_template('dashboard/review.html', sessions=allSessions)

@bp.route('/review/<int:sessionID>')
@login_required
def single_review(sessionID):
    db = get_db()

    if g.user['AccountType'] != 'teacher':
        return redirect('/')
    
    # get session data
    db.execute('SELECT * FROM session WHERE ID = %s', (sessionID,))
    sessionData = db.fetchone()

    # check that teacher can access this session
    db.execute('SELECT CASE WHEN EXISTS (SELECT * FROM `user-to-class` WHERE UserID = %s AND ClassID = %s) THEN 1 ELSE 0 END AS Result', (g.user['ID'], sessionData['ClassID']))
    isInClass = db.fetchone()

    if isInClass == False:
        return redirect('/')

    return render_template('dashboard/single_review.html')

@bp.route('/settings', methods=('GET', 'POST'))
@login_required
def settings():
    if request.method == 'GET':
        return render_template('dashboard/settings.html', hasRecentlySaved = False)
    elif request.method == 'POST':
        db = get_db()

        newFirstName = request.form['first-name']
        newLastName = request.form['last-name']
        newEmail = request.form['email']
        newPassword = request.form['password']

        # check if the user switched back to the default profile picture
        if 'is-default-pfp' in request.form:
            # get rid of the users previous profile picture
            shutil.copyfile('Qearn/static/uploads/default-pfp.jpg', os.path.join('Qearn/static/users', g.user['ProfilePicture']))

        # upload the new profile picture if the user has switched
        if 'has-changed-pfp' in request.form:
            if 'pfp' not in request.files:
                print('not file sent')
                return redirect(request.url)
            
            file = request.files['pfp']
            fileEnding = get_file_ending(file.filename)

            print('got file with file ending', fileEnding)

            # If the user does not select a file, the browser submits an
            # empty file without a filename.
            if file.filename == '':
                print('empty file submitted')
                return redirect(request.url)

            if file and fileEnding in ALLOWED_EXTENSIONS:
                file.save(os.path.join('Qearn/static/users', g.user['ProfilePicture']))

        # update password if the user has entered a new one
        if newPassword != '' and len(newPassword) >= 8:
            db.execute('UPDATE user SET Password = %s WHERE ID = %s', (sha256_crypt.encrypt(newPassword), g.user['ID']))
        
        # update other user data
        db.execute('UPDATE user SET FirstName = %s, LastName = %s, Email = %s WHERE ID = %s', (newFirstName, newLastName, newEmail, g.user['ID']))

        # this function ran before we updated the users information, so we have to run it again
        load_logged_in_user()
        return render_template('dashboard/settings.html', hasRecentlySaved = True)