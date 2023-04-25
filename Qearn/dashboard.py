## Imports ##
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, session
)
from werkzeug.exceptions import abort

import os, shutil

from Qearn.auth import login_required, load_logged_in_user, teacher_required
from Qearn.db import get_db
from Qearn.QuizClass import Quiz
from Qearn.quiz import ClassToRoom, rooms

from passlib.hash import sha256_crypt

## Variables ##

# create the blueprint for all the routes
bp = Blueprint('dashboard', __name__)

# create a list of extensions allowed for images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

## Functions ##
def get_file_ending(filename):
    ending = filename.rsplit('.', 1)[1].lower()
    return ending

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

    # method for users requesting the classrooms they are in
    if request.method == 'GET':
        ## get users classrooms
        db.execute('SELECT * FROM class as c, `user-to-class` as u WHERE (u.ClassID = c.ID) AND (u.UserID = %s)', (g.user['ID'],))
        classes = db.fetchall()

        for classroom in classes:
            # get member count
            db.execute('SELECT COUNT(UserID) as UserCount FROM `user-to-class` WHERE ClassID = %s', (classroom['ID'],))
            member_count = db.fetchone()
            classroom['MemberCount'] = member_count['UserCount']

    # method for users creating a new classroom
    elif request.method == 'POST':
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
            db.execute("INSERT INTO class (SchoolID, ClassName, ClassGroup) VALUES (%s, %s, %s)", (session['SchoolID'], request.form["name"], request.form["age-group"]))
            classId = db.lastrowid
            db.execute("UPDATE class SET HeaderPicture = %s WHERE ID = %s", (f'{classId}.{fileEnding}', classId))
            file.save(os.path.join('Qearn/static/classes', f'{classId}.{fileEnding}'))

            ## add teacher to classroom
            db.execute("INSERT INTO `user-to-class` (UserID, ClassID) VALUES (%s, %s)", (g.user['ID'], classId))

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

    ## get active quiz for this classroom
    currentQuiz = None
    currentQuizID = None
    if classID in ClassToRoom:
        currentQuiz = rooms[ClassToRoom[classID]]
        currentQuizID = ClassToRoom[classID]

    return render_template('dashboard/single_class.html', classData=classData, quizzes=previousQuizzes, currentQuiz=currentQuiz, currentQuizID=currentQuizID)

@bp.route('/classes/<int:classID>/edit', methods=('GET', 'POST'))
@login_required
@teacher_required
def single_class_edit(classID):
    db = get_db()

    if request.method == 'GET':

        ## check user can access this classroom
        db.execute('SELECT CASE WHEN EXISTS (SELECT * FROM `user-to-class` WHERE UserID = %s AND ClassID = %s) THEN 1 ELSE 0 END AS Result', (g.user['ID'], classID))
        isInClass = db.fetchone()

        ## check user is a teacher
        if g.user['AccountType'] != 'teacher':
            return False

        ## get data about this classroom
        db.execute('SELECT * FROM class WHERE ID = %s', (classID,))
        classData = db.fetchone()

        ## get all members in this classroom
        db.execute('SELECT user.* FROM `user-to-class` as uc, user WHERE uc.UserID = user.ID AND uc.ClassID = %s AND user.ID != %s', (classID, g.user['ID']))
        users = db.fetchall()

        ## get all members in the school
        db.execute('SELECT * FROM user WHERE SchoolID = %s AND ID != %s', (classData['SchoolID'], g.user['ID']))
        schoolUsers = db.fetchall()

        return render_template('dashboard/single_class_edit.html', classData=classData, users=users, schoolUsers=schoolUsers)
    elif request.method == 'POST':
        newClassName = request.form['class-name']
        newClassGroup = request.form['class-group']

        # upload the new profile picture if the user has switched
        if 'header-image' in request.files:
            file = request.files['header-image']
            fileEnding = get_file_ending(file.filename)

            # If the user does not select a file, the browser submits an empty file without a filename.
            if file.filename == '':
                return redirect(request.url)

            if file and fileEnding in ALLOWED_EXTENSIONS:
                imageFileName = f'{classID}.{fileEnding}'
                file.save(os.path.join('Qearn/static/classes', imageFileName))
                db.execute('UPDATE class SET HeaderPicture = %s WHERE ID = %s', (imageFileName, classID))


        return redirect(url_for('dashboard.single_class', classID=classID))

@bp.route('/review')
@login_required
@teacher_required
def review():
    # get the database connection
    db = get_db()

    ## get all the session the user has run in every classroom
    db.execute('SELECT session.*, quiz.* FROM `user-to-class` as u, session, quiz WHERE u.UserID = %s and session.ClassID = u.ClassID ORDER BY DateStarted DESC', (g.user['ID']),)
    allSessions = db.fetchall()

    for session in allSessions:
        session['onclick'] = f"window.location='review/{session['ID']}'"

    return render_template('dashboard/review.html', sessions=allSessions)

@bp.route('/review/<int:sessionID>')
@login_required
@teacher_required
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
    
    ## get all data required for page ##

    # get the class data and quiz data
    db.execute('SELECT * FROM class WHERE ID = %s', (sessionData['ClassID'],))
    classData = db.fetchone()

    db.execute('SELECT * FROM quiz WHERE ID = %s', (sessionData['QuizID'],))
    quizData = db.fetchone()

    # we then need to create a dummy quiz so it can load the correct quiz information
    dummyQuiz = Quiz(quizData, classData, timestamp=sessionData['DateStarted'])

    # this dummy quiz only contains quiz information but not student answers
    # so get all student answers related to this session
    db.execute('SELECT * FROM `user-result` WHERE SessionID = %s', (sessionData['ID'],))
    userAnswers = db.fetchall()

    # get the amount of questions that were completed in the quiz
    # (this will be less than the amount of questions in the quiz for cases when the quiz is aborted)
    completedQuestions = len(set([a['QuestionID'] for a in userAnswers]))

    # get the number of users who actually took part in the session
    totalCompetedUsers = len(set([a['UserID'] for a in userAnswers]))

    # get all the users in the class and create a lookup table for the users who took part
    # this lookup table will make it easier to access information when building the html file
    db.execute('SELECT user.* FROM user, `user-to-class` as uc WHERE uc.UserID = user.ID AND uc.ClassID = %s', (sessionData['ClassID'],))
    users = {}
    for user in db.fetchall():
        if user['ID'] in set([a['UserID'] for a in userAnswers]):
            users[user['ID']] = user

    # pre calculate all the user scores
    userScores = {}
    averageCombinedScore = 0

    for id in users:
        user = users[id]
        userScores[id] = {}

        # for every question, get the users answer and calculate a score for it
        for qIndex in range(1, completedQuestions + 1):
            userAnswer = [a['ChosenAnswer'] for a in userAnswers if a['UserID'] == id and a['QuestionID'] == dummyQuiz.layout[qIndex]['question']['ID']][0]
            userScores[id][qIndex] = dummyQuiz.ScoreUserAnswerForQuestion(qIndex, userAnswer)
        
        userScores[id]['Total'] = sum([userScores[id][n] for n in range(1, completedQuestions + 1)])
        averageCombinedScore += userScores[id]['Total']

    averageCombinedScore /= totalCompetedUsers
    
    return render_template('dashboard/single_review.html', quiz=dummyQuiz, answers=userAnswers, completedQuestions=completedQuestions, users=users, userTotal=totalCompetedUsers, userScores=userScores, averageScore=averageCombinedScore)

@bp.route('/settings', methods=('GET', 'POST'))
@login_required
def settings():
    if request.method == 'GET':
        return render_template('dashboard/settings.html', hasRecentlySaved = False)
    elif request.method == 'POST':
        # get a database connection
        db = get_db()

        # get all the data in the submitted form
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
                return redirect(request.url)
            
            file = request.files['pfp']
            fileEnding = get_file_ending(file.filename)

            # If the user does not select a file, the browser submits an empty file without a filename.
            if file.filename == '':
                return redirect(request.url)

            if file and fileEnding in ALLOWED_EXTENSIONS:
                imageFileName = f'{g.user["ID"]}.{fileEnding}'
                file.save(os.path.join('Qearn/static/users', imageFileName))
                db.execute('UPDATE user SET ProfilePicture = %s WHERE ID = %s', (imageFileName, g.user['ID']))

        # update password if the user has entered a new one
        if newPassword != '' and len(newPassword) >= 8:
            db.execute('UPDATE user SET Password = %s WHERE ID = %s', (sha256_crypt.encrypt(newPassword), g.user['ID']))
        
        # update other user data
        db.execute('UPDATE user SET FirstName = %s, LastName = %s, Email = %s WHERE ID = %s', (newFirstName, newLastName, newEmail, g.user['ID']))

        # the users loaded data is now incorrect so we have to load it again
        load_logged_in_user()
        return render_template('dashboard/settings.html', hasRecentlySaved = True)