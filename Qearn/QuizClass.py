from Qearn.db import get_db
from datetime import datetime

class Quiz:
    def __init__(self, quizData, classData, timestamp=datetime.now()):
        db = get_db()

        # get correct version id
        db.execute(
            """
            SELECT ID
            FROM `quiz-version`
            WHERE QuizID = %s AND VersionDate <= %s
            ORDER BY VersionDate DESC
            """,
            (quizData['ID'], timestamp)
        )
        versionID = db.fetchone()['ID']

        print('version is', versionID)

        # get all questions
        db.execute(
            """SELECT *
            FROM question
            WHERE question.QuizID = %s""",
            (quizData['ID'],)
        )
        questions = db.fetchall()
        quizLength = max([q['OrderIndex'] for q in questions])

        # get all answers
        db.execute(
            """SELECT *
            FROM answer
            WHERE answer.QuizID = %s""",
            (quizData['ID'],)
        )
        answers = db.fetchall()

        # get all student users in class
        db.execute("SELECT * FROM user as u, `user-to-class` as uc WHERE u.ID = uc.UserID AND uc.ClassID = %s AND u.AccountType = 'student'", (classData['ID'],))
        classUsers = db.fetchall()

        self.layout = {}
        for i in range(1, quizLength+1):
            data = {}

            # get question with order index 'i'
            currentIndexQuestions = [q for q in questions if q['OrderIndex'] == i if q['QuizVersionID'] <= versionID]
            currentIndexQuestions.sort(key=lambda q: q['QuizVersionID'] - versionID, reverse=True)
            data['question'] = currentIndexQuestions[0]

            # get answers for question
            currentIndexAnswers = [a for a in answers if a['QuestionOrderIndex'] == data['question']['OrderIndex'] if a['QuizVersionID'] <= versionID]
            answersData = []
            answerCount = max([a['AnswerIdentifier'] for a in currentIndexAnswers])

            for aIndex in range(1, answerCount + 1):
                identifierAnswers = [a for a in currentIndexAnswers if a['AnswerIdentifier'] == aIndex]
                identifierAnswers.sort(key=lambda a: a['QuizVersionID'] - versionID, reverse=True)
                answersData.append(identifierAnswers[0])

            data['answers'] = answersData
            
            self.layout[i] = data

        # set other data about the quiz needed for the system
        self.quizData = quizData
        self.classData = classData
        self.classUsers = classUsers
        self.currentQuestionIndex = 1
        self.maxQuestionIndex = len(self.layout)
        self.isRunning = False

        self.dateStarted = datetime.now()
        self.hasSaved = False

        # this is data that would be set by the teacher
        self.questionDelay = 3
        self.questionDuration = 12

        self.studentData = {}
        self.roundAnswers = {}

        self.clients = []
        self.sid_to_user = {}
        self.admin = None

    def IsRunning(self):
        return self.isRunning

    def Start(self):
        self.isRunning = True

    def Next(self):
        if self.currentQuestionIndex < self.maxQuestionIndex:
            self.currentQuestionIndex += 1
            self.roundAnswers = {}
        else:
            self.currentQuestionIndex += 1
            # end quiz here

    def GetQuizData(self):
        return self.quizData
    def GetClassData(self):
        return self.classData
    def GetClassUsers(self):
        return self.classUsers

    def GetCurrentQuestion(self):
        return self.layout[self.currentQuestionIndex]['question']

    def GetCurrentQuestionIndex(self):
        return self.currentQuestionIndex
    
    def GetQuestionCount(self):
        return self.maxQuestionIndex

    def GetQuestionDelay(self):
        return self.questionDelay

    def GetQuestionDuration(self):
        return self.questionDuration

    def GetBasicAnswerData(self):
        # basic answer data is just the answer data but without the "IsCorrect" data
        print("BASIC ANSWER DATA")
        print(id(self.layout[self.currentQuestionIndex]['answers']))
        originalAnswerData = self.layout[self.currentQuestionIndex]['answers'].copy()
        print(id(originalAnswerData))
        for index in range(len(originalAnswerData)):
            pass
            #del originalAnswerData[index]['IsCorrect']

        return originalAnswerData

    def AddAnswerForUser(self, sid, answerString):
        # this stops users from setting their answers more than once
        if sid not in self.roundAnswers:
            self.roundAnswers[sid] = answerString
    
    def GetTotalUserScore(self, sid):
        userData = self.studentData[sid]
        totalScore = sum([userData[qIndex]['score'] for qIndex in userData])

        return totalScore

    def GetCorrectAnswers(self):
        roundAnswers = self.layout[self.currentQuestionIndex]['answers']
        correctAnswers = [a for a in roundAnswers if a['IsCorrect'] == 1]
        return correctAnswers
    
    def ScoreUserAnswerForQuestion(self, questionIndex, userAnswer):
        questionData = self.layout[questionIndex]['question']

        match questionData['QuestionType']:
            case "Basic":
                roundAnswers = self.layout[questionIndex]['answers']
                correctAnswers = [a['AnswerString'] for a in roundAnswers if a['IsCorrect'] == 1]

                return 1000 if userAnswer in correctAnswers else 0
            
        return NotImplementedError

    def EndRound(self):
        ## checks correct answers
        ## awards points
        ## updates user data

        userScores = {}
        currentQuestion = self.GetCurrentQuestion()
        
        print(self.roundAnswers)

        # match currentQuestion['QuestionType']:
        #     case "Basic":
        #         roundAnswers = self.layout[self.currentQuestionIndex]['answers']
        #         correctAnswers = [a['AnswerString'] for a in roundAnswers if a['IsCorrect'] == 1]

        #         for sid in self.GetStudents():
        #             userScore = 0

        #             if sid in self.roundAnswers:
        #                 userAnswer = self.roundAnswers[sid]
        #                 userScore = 1000 if userAnswer in correctAnswers else 0

        #             userScores[sid] = userScore
        
        for sid in self.GetStudents():
            userScore = 0

            if sid in self.roundAnswers:
                userAnswer = self.roundAnswers[sid]
                userScore = self.ScoreUserAnswerForQuestion(self.currentQuestionIndex, userAnswer)

            userScores[sid] = userScore

        for sid in userScores:
            self.studentData[sid][self.currentQuestionIndex] = {
                "score": userScores[sid],
                "answer": self.roundAnswers[sid] if sid in self.roundAnswers else None,
            }

        return userScores

    def AddStudent(self, sid, user_id):
        self.clients.append(sid)
        self.sid_to_user[sid] = user_id
        if sid not in self.studentData:
            self.studentData[sid] = {}
    def RemoveStudent(self, sid):
        self.clients.remove(sid)
        del self.sid_to_user[sid]
    def GetStudents(self):
        return self.clients
    
    def SetAdmin(self, sid):
        self.admin = sid
    def RemoveAdmin(self):
        self.admin = None
    def GetAdmin(self):
        return self.admin
    
    def SaveQuizInDatabase(self):
        if self.hasSaved:
            return
        self.hasSaved = True

        db = get_db()

        ## insert a session into the database
        db.execute('INSERT INTO session (DateStarted, QuizID, ClassID) VALUES (%s, %s, %s)', (self.dateStarted, self.quizData['ID'], self.classData['ID']))
        sessionId = db.lastrowid

        ## insert user results
        for sid in self.GetStudents():
            userId = self.sid_to_user[sid]
            for questionIndex in range(1, self.maxQuestionIndex + 1):
                answerString = self.studentData[sid][questionIndex]['answer']

                if answerString == None:
                    answerString = ""

                questionId = self.layout[questionIndex]['question']['ID']
                db.execute('INSERT INTO `user-result` (UserID, SessionID, QuestionID, ChosenAnswer) VALUES (%s, %s, %s, %s)',
                            (userId, sessionId, questionId, answerString))

                


## quiz life cycle

# state = lobby
# users from the class can join and leave during this period

# state = running
# users that were already in the game can join back
# 


## important things needed for my quiz system
# people join the quiz using websockets
# people send and recieve data about the quiz using websockets
# when and how do I send data about the websocket? The admin calls the next round.