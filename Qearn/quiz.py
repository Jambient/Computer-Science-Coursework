## Imports ##
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app, abort, session
)
from flask_socketio import emit, join_room, leave_room
from flask_socketio import rooms as get_rooms
from werkzeug.exceptions import abort

from Qearn.auth import login_required, teacher_required
from Qearn.db import get_db
from Qearn.QuizClass import Quiz

from Qearn import socketio

import time, random

## Variables ##

# create a blueprint for all the routes
bp = Blueprint('quiz', __name__, url_prefix='/')

rooms = {} # lookup table storing roomIds -> room info
ClassToRoom = {} # lookup table storing classIds -> roomIds

## Functions ##
@bp.route('/quizzes')
@teacher_required
def quizzes():
    if 'q' not in request.args:
        return render_template('quiz/quizzes.html', quizzes=[], qeury="")
    else:
        query = request.args['q']

        db = get_db()
        search = "|".join([w.lower() for w in query.split(' ')])
        print(search)

        # THIS CAUSES AN SQL INJECTION EXPLOIT - MUST FIX AT SOME POINT
        db.execute('SELECT * FROM quiz WHERE Name REGEXP "[[:<:]]({})"'.format(search))
        results = db.fetchall()

        return render_template('quiz/quizzes.html', quizzes=results, query=query)

@bp.route('/quizzes/<int:quizID>')
@teacher_required
def single_quiz(quizID):
    db = get_db()

    # get quiz data
    db.execute('SELECT * FROM quiz WHERE ID = %s', (quizID,))
    quizData = db.fetchone()

    if not quizData:
        abort(404)

    # we then need to create a dummy quiz so it can load the correct quiz information
    # the build of the quiz requires class data so we also pass in dummy data
    dummyQuiz = Quiz(quizData, {"ID": 1})

    # get owner data
    db.execute('SELECT * FROM user WHERE ID = %s', (quizData['OwnerUserID'],))
    owner = db.fetchone()
    dummyQuiz.owner = owner

    db.execute('SELECT SchoolName FROM school WHERE ID = %s', (dummyQuiz.owner['SchoolID'],))
    school_name = db.fetchone()
    dummyQuiz.owner['SchoolName'] = school_name['SchoolName']

    # get user classes
    db.execute('SELECT * FROM `user-to-class` AS u, class AS c WHERE u.UserID = %s AND c.ID = u.ClassID', (g.user['ID'],))
    user_classes = db.fetchall()

    return render_template('quiz/single_quiz.html', quiz=dummyQuiz, classes=user_classes)

@bp.route('/create')
@teacher_required
def create_quiz():
    return render_template('quiz/create.html')

## Socket Functions ##
def getUsersRoom(sid):
    userRooms = get_rooms(sid)
    userRooms.remove(sid)
    print(userRooms)
    currentRoomId = 0
    if len(userRooms) > 0:
        currentRoomId = userRooms[0]
    else:
        return False
    return currentRoomId

@socketio.on('connect')
def connect():
    print("socket connected")
    if len(session) == 0:
        print("user does not have an account")
        return False
    else:
        print("user is authenticated")
        print(session['ID'])
        socketio.emit('id', request.sid, to=request.sid)

@socketio.on('disconnect')
def disconnect():
    currentRoomId = getUsersRoom(request.sid)
    if not currentRoomId:
        print('error in current room id')
        return
    
    if currentRoomId not in rooms:
        return
    
    room = rooms[currentRoomId]
    
    if session['AccountType'] == 'student':
        room.RemoveStudent(request.sid)
    elif session['AccountType'] == 'teacher':
        room.RemoveAdmin()

    # close down the room if all users have left (including the admin)
    if len(room.GetStudents()) == 0 and room.GetAdmin() == None:
        print('SHUTTING DOWN THE ROOM')
        del rooms[currentRoomId]

        if room.classData['ID'] in ClassToRoom:
            del ClassToRoom[room.classData['ID']]

@socketio.on('join')
def student_join(roomID):
    print("user is requesting to join a quiz with id", roomID)

    ## verify the quiz exists in server memory
    if not roomID in rooms: return False
    room = rooms[roomID]

    ## check the quiz is not already running
    print(room.IsRunning())

    ## enable this check after DEBUGGING
    # if room.IsRunning():
    #     return False

    ## verify the user is part of that class

    ## put user into room
    print("successfully joined room")
    join_room(roomID)
    print(session)
    if session['AccountType'] == 'student':
        print('student requested to join')
        room.AddStudent(request.sid, session['ID'])

        if room.GetAdmin() != None:
            socketio.emit('new student', [room.sid_to_user[key] for key in room.sid_to_user.keys()], to=room.GetAdmin()['SID'])
    else:
        print('teacher requested to join')
        if room.GetAdmin() == None or room.GetAdmin()['ID'] == session['ID']:
            print('teacher is allowed in')
            room.SetAdmin(request.sid, session['ID'])
            socketio.emit('new student', [room.sid_to_user[key] for key in room.sid_to_user.keys()], to=room.GetAdmin()['SID'])
        else:
            print('teacher is not allowed in')
            pass
            # the room already has a teacher, so tell the user this somehow

@socketio.on('latency-ping')
def latency_ping():
    socketio.emit('latency-pong', to=request.sid)

@socketio.on('start')
def teacher_start(quizSettings):
    print("a teacher is attempting to start the quiz", quizSettings)

    # get the rooms the teacher is in
    currentRoomId = getUsersRoom(request.sid)
    if not currentRoomId:
        print('error in current room id')
        return False
    
    if currentRoomId not in rooms:
        return redirect('/')
    
    room = rooms[currentRoomId]

    print('starting quiz')

    room.Start()

    for sid in room.GetStudents():
        print(sid)

    # set settings in quiz and make sure the values are valid
    room.questionDelay =  max(1, min(int(quizSettings.pop('questionDelay', 3)), 20))
    room.questionDuration =  max(1, min(int(quizSettings.pop('questionDuration', 12)), 60))
    room.timeBasedPoints = True if quizSettings.pop('hasTimeBasedScoring', None) != None else False

    # run questions
    while room.GetCurrentQuestionIndex() <= room.GetQuestionCount():
        socketio.emit('run question', {
            'questionNumber': room.GetCurrentQuestionIndex(), 
            'maxQuestions': room.GetQuestionCount(), 
            'questionData': room.GetCurrentQuestion(), 
            'answerData': room.GetBasicAnswerData(),
            'questionDelay': room.GetQuestionDelay(),
            'questionTime': room.GetQuestionDuration()
        }, to=currentRoomId)

        # wait till end of current round
        timePassed = 0
        while timePassed < room.GetQuestionDelay() + room.GetQuestionDuration():
            time.sleep(0.5)
            timePassed += 0.5

            # check if all players have answered the question
            if len(room.roundAnswers) == len(room.GetStudents()):
                break

        # get user scores
        userScores = room.EndRound()
        print("user scores:", userScores)
        print("room users:", room.GetStudents())

        # send data to the client
        for sid in userScores:
            socketio.emit('answer status', [userScores[sid], room.GetCorrectAnswers()], to=sid)

        time.sleep(3)

        room.Next()

    print('quiz ended')
    for sid in room.GetStudents():
        print(sid)
        socketio.emit('end', [room.GetTotalUserScore(sid), room.GetQuestionCount()*1000], to=sid)

    print('ending quiz and notifying admin', room.GetAdmin())

    socketio.emit('end', to=room.GetAdmin()['SID'])
    
    
@socketio.on('answer')
def student_answer(answerString):
    print(request.sid)
    print(answerString)

    currentRoomId = getUsersRoom(request.sid)
    if not currentRoomId:
        print('error in current room id')
        return False
    room = rooms[currentRoomId]

    room.AddAnswerForUser(request.sid, answerString)

@socketio.on('save')
def quiz_save():
    currentRoomId = getUsersRoom(request.sid)
    room = rooms[currentRoomId]

    print('save request')

    # make sure the requesting user is the admin of the room
    # if request.sid != room.GetAdmin():
    #     print('user is not room admin')
    #     return False
    
    print('SAVING QUIZ')
    
    # save the quiz
    room.SaveQuizInDatabase()

@bp.route('/api/quiz/run', methods=('POST',))
def run_quiz():
    ## verify user is signed in
    if len(session) == 0:
        return 'Account required', 401

    ## verify user is a teacher
    if g.user['AccountType'] != 'teacher':
        return 'Teacher account required.', 401
    
    ## verify that all information is included in the request
    requestData = request.get_json(force=True)
    quizID = requestData["quizID"]
    classID = requestData["classID"]

    if not quizID:
        return 'quizID is null', 500
    if not classID:
        return 'classID is null', 500

    ## get database
    database = get_db()

    ## verify quiz exists
    database.execute("SELECT * FROM quiz WHERE ID = %s", (quizID,))
    quizData = database.fetchone()

    if not quizData:
        return 'quizID is invalid', 500

    ## verify class exists
    database.execute("SELECT * FROM class WHERE ID = %s", (classID,))
    classData = database.fetchone()

    if not classData:
        return 'classID is invalid', 500

    ## verify that teacher is owner of classID
    database.execute("SELECT * FROM `user-to-class` WHERE UserID = %s AND ClassID = %s", (g.user['ID'], classID))
    isTeacherClassOwner = database.fetchone()

    if not isTeacherClassOwner:
        return 'Class authentication error', 401

    ## set up a new room
    roomCode = random.randint(111111, 999999)
    print('success', roomCode)

    rooms[roomCode] = Quiz(quizData, classData)
    ClassToRoom[classData['ID']] = roomCode

    return str(roomCode), 201

@bp.route('/quiz/<int:roomID>')
@login_required
def quiz(roomID):

    # check that quiz exists
    if roomID not in rooms:
        return abort(404)
    
    # check user can access the room
    database = get_db()
    database.execute('SELECT CASE WHEN EXISTS (SELECT * FROM `user-to-class` WHERE UserID = %s AND ClassID = %s) THEN 1 ELSE 0 END AS Result', (g.user['ID'], rooms[roomID].GetClassData()['ID']))
    isInClass = database.fetchone()
    
    if isInClass['Result'] == 0:
        return redirect('/')
    
    if g.user['AccountType'] == 'student':
        return render_template('quiz/student.html', quiz=rooms[roomID])
    else:
        return render_template('quiz/teacher.html', roomID=roomID, classData=rooms[roomID].GetClassData(), classUsers=rooms[roomID].GetClassUsers())