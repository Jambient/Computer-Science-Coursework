## Imports ##
import os, random, time
from flask import Flask, session, g, request, render_template, redirect, abort
from flask_socketio import SocketIO
from flask_socketio import rooms as get_rooms
from Qearn.QuizClass import Quiz

## Variables ##

# initialise the flask app
app = Flask(__name__, instance_relative_config=True)

# initialise the sockets system
socketio = SocketIO(app, cors_allowed_origins='*')

## Functions ##
# def getUsersRoom(sid):
#     userRooms = get_rooms(sid)
#     userRooms.remove(sid)
#     print(userRooms)
#     currentRoomId = 0
#     if len(userRooms) > 0:
#         currentRoomId = userRooms[0]
#     else:
#         return False
#     return currentRoomId

## Main Code ##
# @socketio.on('connect')
# def connect():
#     print("socket connected")
#     if len(session) == 0:
#         print("user does not have an account")
#         return False
#     else:
#         print("user is authenticated")
#         print(session['ID'])
#         socketio.emit('id', request.sid, to=request.sid)

# @socketio.on('disconnect')
# def disconnect():
#     currentRoomId = getUsersRoom(request.sid)
#     if not currentRoomId:
#         print('error in current room id')
#         return
    
#     if currentRoomId not in rooms:
#         return
    
#     room = rooms[currentRoomId]
    
#     if session['AccountType'] == 'student':
#         room.RemoveStudent(request.sid)
#     elif session['AccountType'] == 'teacher':
#         room.RemoveAdmin()

#     # close down the room if all users have left (including the admin)
#     if len(room.GetStudents()) == 0 and room.GetAdmin() == None:
#         print('SHUTTING DOWN THE ROOM')
#         del rooms[currentRoomId]

#         if room.classData['ID'] in ClassToRoom:
#             del ClassToRoom[room.classData['ID']]

# @socketio.on('join')
# def student_join(roomID):
#     print("user is requesting to join a quiz with id", roomID)

#     ## verify the quiz exists in server memory
#     if not roomID in rooms: return False
#     room = rooms[roomID]

#     ## check the quiz is not already running
#     print(room.IsRunning())

#     ## enable this check after DEBUGGING
#     # if room.IsRunning():
#     #     return False

#     ## verify the user is part of that class

#     ## put user into room
#     print("successfully joined room")
#     join_room(roomID)
#     print(session)
#     if session['AccountType'] == 'student':
#         print('student requested to join')
#         room.AddStudent(request.sid, session['ID'])

#         if room.GetAdmin() != None:
#             socketio.emit('new student', [room.sid_to_user[key] for key in room.sid_to_user.keys()], to=room.GetAdmin()['SID'])
#     else:
#         print('teacher requested to join')
#         if room.GetAdmin() == None or room.GetAdmin()['ID'] == session['ID']:
#             print('teacher is allowed in')
#             room.SetAdmin(request.sid, session['ID'])
#             socketio.emit('new student', [room.sid_to_user[key] for key in room.sid_to_user.keys()], to=room.GetAdmin()['SID'])
#         else:
#             print('teacher is not allowed in')
#             pass
#             # the room already has a teacher, so tell the user this somehow

# @socketio.on('latency-ping')
# def latency_ping():
#     socketio.emit('latency-pong', to=request.sid)

# @socketio.on('start')
# def teacher_start(quizSettings):
#     print("a teacher is attempting to start the quiz", quizSettings)

#     # get the rooms the teacher is in
#     currentRoomId = getUsersRoom(request.sid)
#     if not currentRoomId:
#         print('error in current room id')
#         return False
    
#     if currentRoomId not in rooms:
#         return redirect('/')
    
#     room = rooms[currentRoomId]

#     print('starting quiz')

#     room.Start()

#     for sid in room.GetStudents():
#         print(sid)

#     # set settings in quiz and make sure the values are valid
#     room.questionDelay =  max(1, min(int(quizSettings.pop('questionDelay', 3)), 20))
#     room.questionDuration =  max(1, min(int(quizSettings.pop('questionDuration', 12)), 60))
#     room.timeBasedPoints = True if quizSettings.pop('hasTimeBasedScoring', None) != None else False

#     # run questions
#     while room.GetCurrentQuestionIndex() <= room.GetQuestionCount():
#         socketio.emit('run question', {
#             'questionNumber': room.GetCurrentQuestionIndex(), 
#             'maxQuestions': room.GetQuestionCount(), 
#             'questionData': room.GetCurrentQuestion(), 
#             'answerData': room.GetBasicAnswerData(),
#             'questionDelay': room.GetQuestionDelay(),
#             'questionTime': room.GetQuestionDuration()
#         }, to=currentRoomId)

#         # wait till end of current round
#         timePassed = 0
#         while timePassed < room.GetQuestionDelay() + room.GetQuestionDuration():
#             time.sleep(0.5)
#             timePassed += 0.5

#             # check if all players have answered the question
#             if len(room.roundAnswers) == len(room.GetStudents()):
#                 break

#         # get user scores
#         userScores = room.EndRound()
#         print("user scores:", userScores)
#         print("room users:", room.GetStudents())

#         # send data to the client
#         for sid in userScores:
#             socketio.emit('answer status', [userScores[sid], room.GetCorrectAnswers()], to=sid)

#         time.sleep(3)

#         room.Next()

#     print('quiz ended')
#     for sid in room.GetStudents():
#         print(sid)
#         socketio.emit('end', [room.GetTotalUserScore(sid), room.GetQuestionCount()*1000], to=sid)

#     print('ending quiz and notifying admin', room.GetAdmin())

#     socketio.emit('end', to=room.GetAdmin()['SID'])
    
    
# @socketio.on('answer')
# def student_answer(answerString):
#     print(request.sid)
#     print(answerString)

#     currentRoomId = getUsersRoom(request.sid)
#     if not currentRoomId:
#         print('error in current room id')
#         return False
#     room = rooms[currentRoomId]

#     room.AddAnswerForUser(request.sid, answerString)

# @socketio.on('save')
# def quiz_save():
#     currentRoomId = getUsersRoom(request.sid)
#     room = rooms[currentRoomId]

#     print('save request')

#     # make sure the requesting user is the admin of the room
#     # if request.sid != room.GetAdmin():
#     #     print('user is not room admin')
#     #     return False
    
#     print('SAVING QUIZ')
    
#     # save the quiz
#     room.SaveQuizInDatabase()

app.config.from_pyfile('config.py')

try:
    os.makedirs(app.instance_path)
except OSError:
    pass

from . import db
db.init_app(app)

from . import auth
app.register_blueprint(auth.bp)

from . import dashboard
app.register_blueprint(dashboard.bp)
app.add_url_rule('/', endpoint='index')

from . import quiz
quiz_blueprint = quiz.bp

@quiz_blueprint.route('/api/accounts/email/<string:email>')
def check_email(email):
    database = db.get_db()
    database.execute("SELECT email FROM user WHERE email = %s", (email,))
    doesEmailExist = database.fetchone()

    if doesEmailExist:
        return 'True'
    else:
        return 'False'

@quiz_blueprint.route('/api/schools/<string:schoolCode>')
def check_school(schoolCode):
    schoolCode = schoolCode.upper()

    database = db.get_db()
    database.execute("SELECT * FROM school WHERE SchoolCode = %s", (schoolCode,))
    doesSchoolExist = database.fetchone()

    if doesSchoolExist:
        return 'True'
    else:
        return 'False'

app.register_blueprint(quiz_blueprint)

@app.errorhandler(404)
def page_not_found(e): 
    return render_template('404.html'), 404

if __name__ == '__main__':
    socketio.run(app, port=3000)