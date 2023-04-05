from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app, abort
)
from flask_socketio import SocketIO, emit, join_room
from werkzeug.exceptions import abort

from Qearn.auth import login_required
from Qearn.db import get_db

bp = Blueprint('quiz', __name__, url_prefix='/')

@bp.route('/quizzes')
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

        for result in results:
            ## get number of questions
            db.execute('SELECT COUNT(QuizID) as QuestionCount FROM question WHERE QuizID = %s', (result['ID'],))
            result['QuestionCount'] = db.fetchone()['QuestionCount']

        print(results)
        return render_template('quiz/quizzes.html', quizzes=results, query=query)

@bp.route('/quizzes/<int:quizID>')
def single_quiz(quizID):
    db = get_db()

    # get quiz data
    db.execute('SELECT * FROM quiz WHERE ID = %s', (quizID,))
    quiz = db.fetchone()

    if not quiz:
        abort(404)

    # get questions
    db.execute('SELECT * FROM question WHERE QuizID = %s ORDER BY OrderIndex', (quizID,))
    questions = db.fetchall()
    quiz['Questions'] = questions

    # get answers
    db.execute('SELECT * FROM answer WHERE QuizID = %s', (quizID,))
    answers = db.fetchall()

    # set answers
    for question in quiz['Questions']:
        question['Answers'] = [a for a in answers if a['QuestionOrderIndex'] == question['OrderIndex']]

    # get owner data
    db.execute('SELECT * FROM user WHERE ID = %s', (quiz['OwnerUserID'],))
    owner = db.fetchone()
    quiz['Owner'] = owner

    db.execute('SELECT SchoolName FROM school WHERE ID = %s', (quiz['Owner']['SchoolID'],))
    school_name = db.fetchone()
    quiz['Owner']['SchoolName'] = school_name['SchoolName']

    # get user classes
    db.execute('SELECT * FROM `user-to-class` AS u, class AS c WHERE u.UserID = %s AND c.ID = u.ClassID', (g.user['ID'],))
    user_classes = db.fetchall()

    return render_template('quiz/single_quiz.html', quiz=quiz, classes=user_classes)

@bp.route('/quiz/sandbox')
def test_area():
    return render_template('quiz/sandbox.html')

@bp.route('/create')
def create_quiz():
    return render_template('quiz/create.html')