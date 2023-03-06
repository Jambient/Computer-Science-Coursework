from Qearn.db import get_db

class Quiz:
    def __init__(self, quizID):

        db = get_db()

        # we can assume the quiz id links to a quiz as this would have been verified previously

        # get all questions
        db.execute(
            """SELECT ID, QuestionString, QuestionType, OrderIndex
            FROM question
            WHERE (question.QuizID = %s)""",
            (quizID,)
        )
        questions = db.fetchall()

        # get all answers
        db.execute(
            """SELECT ID, QuestionID, AnswerString, IsCorrect
            FROM answer
            WHERE (answer.QuizID = %s)""",
            (quizID,)
        )
        answers = db.fetchall()

        self.layout = {}
        for i in range(1, len(questions)+1):
            data = {}

            # get question with order index 'i'
            questionData = [q for q in questions if q['OrderIndex'] == i]
            data['question'] = questionData[0]

            # get answers for question
            answersData = [a for a in answers if a['QuestionID'] == data['question']['ID']]
            data['answers'] = answersData
            
            self.layout[i] = data

        # set other data about the quiz needed for the system
        self.currentQuestionIndex = 1
        self.maxQuestionIndex = len(questions)
        self.isRunning = False

        # this is data that would be set by the teacher
        self.questionDelay = 3
        self.questionDuration = 10

        self.studentData = {}
        self.roundAnswers = {}

        self.clients = []

    def IsRunning(self):
        return self.isRunning

    def Start(self):
        self.isRunning = True

    def Next(self):
        if self.currentQuestionIndex < self.maxQuestionIndex:
            self.studentData[self.currentQuestionIndex]= self.roundAnswers
            self.currentQuestionIndex += 1
            self.roundAnswers = {}
        else:
            pass
            # end quiz here

    def GetCurrentQuestion(self):
        return self.layout[self.currentQuestionIndex]['question']

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

    def AddAnswerForUser(self, uniqueId, answerId):
        # this stops users from setting their answers more than once
        if uniqueId not in self.roundAnswers:
            self.roundAnswers[uniqueId] = answerId

    def GetCorrectAnswer(self):
        print('GETTING CORRECT ANSWER')
        roundAnswers = self.layout[self.currentQuestionIndex]['answers']
        print(roundAnswers)
        correctAnswer = [a for a in roundAnswers if a['IsCorrect'] == 1]
        return correctAnswer[0]

    def CheckRoundAnswers(self):
        isCorrect = {}
        correctAnswer = self.GetCorrectAnswer()
        for id in self.roundAnswers:
            answerId = self.roundAnswers[id]
            isCorrect[id] = answerId == correctAnswer['ID']

        return isCorrect

    def AddStudent(self, sid):
        self.clients.append(sid)
    def RemoveStudent(self, sid):
        self.clients.remove(sid)
    def GetStudents(self):
        return self.clients


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