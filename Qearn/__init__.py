## Imports ##
import os, random, time
from flask import Flask, session, g, request, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_socketio import rooms as get_rooms
from Qearn.QuizClass import Quiz

## Variables ##
app = Flask(__name__, instance_relative_config=True)
socketio = SocketIO(app, cors_allowed_origins='*') #http://127.0.0.1:5000')

rooms = {}

## Functions ##

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

## Main Code ##
@socketio.on('connect')
def connect():
    print("socket connected")
    if len(session) == 0:
        print("user does not have an account")
        return False
    else:
        print("user is authenticated")
        print(session['user_id'])
        socketio.emit('id', request.sid, to=request.sid)

@socketio.on('disconnect')
def disconnect():
    currentRoomId = getUsersRoom(request.sid)
    if not currentRoomId:
        print('error in current room id')
        return False
    room = rooms[currentRoomId]
    room.RemoveStudent(request.sid)

@socketio.on('join')
def student_join(roomID):
    print("user is requesting to join a quiz with id", roomID)

    ## verify the quiz exists in server memory
    if not roomID in rooms: return False
    room = rooms[roomID]

    ## check the quiz is not already running
    print(room.IsRunning())
    if room.IsRunning():
        return False

    ## verify the user is part of that class

    ## put user into room
    print("successfully joined room")
    join_room(roomID)
    room.AddStudent(request.sid)


@socketio.on('start')
def teacher_start():
    print("a teacher is attempting to start the quiz")

    # get the rooms the teacher is in

    currentRoomId = getUsersRoom(request.sid)
    if not currentRoomId:
        print('error in current room id')
        return False
    room = rooms[currentRoomId]

    print('starting quiz')

    room.Start()

    # run first question
    for i in range(room.GetQuestionCount()):
        currentTime = time.time()
        socketio.emit('run question', {
            'questionNumber': 1, 
            'maxQuestions': room.GetQuestionCount(), 
            'questionData': room.GetCurrentQuestion(), 
            'answerData': room.GetBasicAnswerData(),
            'startTime': currentTime + room.GetQuestionDelay(),
            'endTime': currentTime + room.GetQuestionDelay() + room.GetQuestionDuration()
        }, to=currentRoomId)

        # wait till end of current round
        time.sleep(room.GetQuestionDelay() + room.GetQuestionDuration())

        # check users answers
        isCorrect = room.CheckRoundAnswers()
        print(isCorrect)

        print(room.GetStudents())

        socketio.emit('answer status', isCorrect, to=currentRoomId)
        time.sleep(3)

        room.Next()
    
    
@socketio.on('answer')
def student_answer(answerId):
    print(request.sid)
    print(answerId)

    currentRoomId = getUsersRoom(request.sid)
    if not currentRoomId:
        print('error in current room id')
        return False
    room = rooms[currentRoomId]

    room.AddAnswerForUser(request.sid, answerId)

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

@quiz_blueprint.route('/api/quiz/run', methods=('POST',))
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
    database = db.get_db()

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

    rooms[roomCode] = Quiz(quizID)

    return str(roomCode), 201

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

@quiz_blueprint.route('/quiz/<roomID>')
#@login_required
def quiz(roomID):
    # VERIFY THAT THE STUDENT IS A PART OF THE CLASS THAT IS RUNNING THE QUIZ
    # OR THEY ARE A GUEST IF I END UP ADDING THAT FEATURE

    # check that quiz exists
    roomID = int(roomID)
    if roomID not in rooms:
        return render_template('404.html')
    
    if g.user['AccountType'] == 'student':
        return render_template('quiz/student.html')
    else:
        return render_template('quiz/teacher.html')

app.register_blueprint(quiz_blueprint)

@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 404

    # print('Connected!', file=os.getenv().stderr)
    # app.logger.info("Connected!")
    # emit('after connect', {'data': 'Hi there'})

# @socketio.on('sup')
# def test_send():
#     print('recieved message')

# @socketio.on('message')
# def handle_message(data):
#     app.logger.info("Connected!")
#     print('received message: ' + data)

if __name__ == '__main__':
    socketio.run(app, port=3000)

# def create_app(test_config=None):
#     # create and configure the app
#     #app = Flask(__name__, instance_relative_config=True)

#     if test_config is None:
#         # load the instance config, if it exists, when not testing
#         app.config.from_pyfile('config.py')
#     else:
#         # load the test config if passed in
#         app.config.from_mapping(test_config)

#     # ensure the instance folder exists
#     try:
#         os.makedirs(app.instance_path)
#     except OSError:
#         pass

#     from . import db
#     db.init_app(app)

#     from . import auth
#     app.register_blueprint(auth.bp)

#     from .import quiz
#     quiz.init_sockets(app)
#     app.register_blueprint(quiz.bp)

#     from . import dashboard
#     app.register_blueprint(dashboard.bp)
#     app.add_url_rule('/', endpoint='index')

#     # socketio = SocketIO(app)

#     # @socketio.on('connection')
#     # def connect_handler():
#     #     print('got connection!')
#     #     emit('confirm', {'data': 'Successful'})

#     # socketio.run(app, host='0.0.0.0')

#     return app