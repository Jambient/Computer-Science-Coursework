console.log('initialised')

var LATENCY = 30
var LAST_LATENCY = 30
var latencyTotalTime = 0
var latencyRequestCount = 0
var latencyStartTime;

// get all pages
let pages = document.getElementsByClassName('page')
let answerTypes = document.getElementsByClassName('answer')[0].children

function showPage(pageId) {
    let page = document.getElementById(pageId)

    page.classList.remove('hide')
    for (let p of pages) {
        if (p.id != pageId) {
            p.classList.add('hide')
        }
    }
}
function getPage(pageId) {
    return document.getElementById(pageId)
}

function showAnswerType(answerId) {
    let answerType = document.getElementById(answerId)

    answerType.classList.remove('hide')
    for (let a of answerTypes) {
        if (a.id != answerId) {
            a.classList.add('hide')
        }
    }
}
function getAnswerTypeElement(answerId) {
    return document.getElementById(answerId)
}

function initialiseTimer(element) {
    var options = {
        time:  element.getAttribute('data-time') || 15,
        maxTime: element.getAttribute('data-maxtime') || 25,
        lineWidth: element.getAttribute('data-line') || 4,
        rotate: element.getAttribute('data-rotate') || 0,
        size: element.getAttribute('data-size') || 60
    }

    var canvas = element.querySelector('canvas')
    var centerText = element.querySelector('h3')

    var ctx = canvas.getContext('2d');
    ctx.translate(options.size / 2, options.size / 2); // change center
    ctx.rotate((-1 / 2 + options.rotate / 180) * Math.PI); // rotate -90 deg

    var radius = (options.size - options.lineWidth) / 2;

    var drawCircle = function(color, options) {
        ctx.clearRect(-canvas.width, -canvas.height, canvas.width * 2, canvas.height * 2)
        centerText.innerHTML = Math.max(Math.ceil(options.time), 0)
        let percent = options.time / options.maxTime

		percent = Math.min(Math.max(0, percent), 1);
		ctx.beginPath();
		ctx.arc(0, 0, radius, 0, Math.PI * 2 * percent, false);
		ctx.strokeStyle = color;
        ctx.lineCap = 'round';
		ctx.lineWidth = options.lineWidth
		ctx.stroke();
    };

    return [options, drawCircle]
}

var [timerOptions, drawCircleFunction] = initialiseTimer(document.querySelector('#question .timer'));

const socket = io.connect();

socket.on('connect',()=>{
    // get current room id
    let url_data = window.location.pathname.split("/")
    let roomID = parseInt(url_data[url_data.length - 1])

    // join the room on the server
    socket.emit("join", roomID)
})

setInterval(function() {
    latencyStartTime = Date.now();
    socket.emit("latency-ping")
}, 1000)
socket.on("latency-pong", () => {
    let latency = (Date.now() - latencyStartTime) / 2
    latencyTotalTime += latency
    latencyRequestCount += 1

    LAST_LATENCY = latency
    LATENCY = latencyTotalTime / latencyRequestCount
})

var globalCountInterval
var isCountIntervalRunning = false

socket.on('run question', (data)=>{
    console.log('recieved run question')
    console.log(data)

    showPage('countdown')
    showAnswerType(data['questionData']['QuestionType'])
    let countDownPage = getPage('countdown')
    let preCountNum = countDownPage.querySelector('.top-layer h1')
    let duringCountNum = document.querySelector('.timer h1')

    let basicAnswerPage = getAnswerTypeElement('Basic')

    // set question page
    document.querySelector('#current-question span').innerHTML = data['questionNumber']
    document.getElementById('question-total').innerHTML = `/ ${data['maxQuestions']}`
    document.querySelector('.question h1').innerHTML = data['questionData']['QuestionString']

    basicAnswerPage.innerHTML = ''
    for (let answer of data['answerData']) {
        let button = document.createElement('button')
        button.innerHTML = answer['AnswerString']
        basicAnswerPage.appendChild(button)

        button.onclick = function() {
            socket.emit('answer', answer['AnswerString'])
            console.log(answer['AnswerString'])
            showPage('waiting')
        }
    }

    // the promise for the pre question timer
    new Promise((resolve, reject) => {
        var preQuestionTime = data['questionDelay']*1000 - LAST_LATENCY
        var preQuestionStartTime = Date.now()

        var countInterval = setInterval(function() {
            if (Date.now() - preQuestionStartTime >= preQuestionTime) {
                clearInterval(countInterval)
                resolve()
            }

            let difference = Math.ceil((preQuestionTime - (Date.now() - preQuestionStartTime)) / 1000).toString();
            preCountNum.innerHTML = difference
        }, 200);
    }).then(() => {
        showPage('question')

        // the promise for the during question timer
        if (isCountIntervalRunning) {
            clearInterval(globalCountInterval)
            isCountIntervalRunning = false
        }

        
        var questionTime = data['questionTime']*1000 - LAST_LATENCY
        var questionStartTime = Date.now()

        timerOptions.maxTime = data['questionTime']
        timerOptions.time = timerOptions.maxTime
        new Promise((resolve, reject) => {
            isCountIntervalRunning = true
            globalCountInterval = setInterval(function() {
                if (Date.now() - questionStartTime >= questionTime) {
                    clearInterval(globalCountInterval)
                    isCountIntervalRunning = false
                    resolve()
                }

                timerOptions.time = (questionTime - (Date.now() - questionStartTime)) / 1000
                drawCircleFunction('#16A086', timerOptions)
            }, 200);
        });
    });
})

socket.on('answer status', (answerData)=>{
    userScore = answerData[0]
    correctAnswers = answerData[1]
    console.log(correctAnswers)

    if (userScore == 0) {
        correctAnswerNode = document.querySelector('#incorrect .correct-answer')
        correctNodeContainer = document.querySelector('#incorrect .correct-answer-container')
        
        // delete previous nodes
        correctNodeContainer.innerHTML = ''
        
        // add new ones
        for (var answer of correctAnswers) {
            newAnswerNode = correctAnswerNode.cloneNode()
            newAnswerNode.innerHTML = answer['AnswerString']
            newAnswerNode.classList.remove('hide')
            correctNodeContainer.appendChild(newAnswerNode)
        }

        showPage('incorrect')
    } else {
        userScoreNode = document.querySelector('#correct-user-score')
        userScoreNode.innerHTML = '+' + userScore
        showPage('correct')
    }
})

socket.on('end', (scoreData)=>{
    let userPointsNode = document.querySelector('#end .points')
    let maxScoreNode = document.querySelector('#end .max-points')
    let messageNode = document.querySelector('#end .message')

    userPointsNode.innerHTML = scoreData[0]
    maxScoreNode.innerHTML = `out of ${scoreData[1]}`

    // set the message based on the percentage score
    let percentageScore = scoreData[0] / scoreData[1]
    if (percentageScore <= 0.2) {
        messageNode.innerHTML = 'Better luck next time!'
    } else if (percentageScore <= 0.5) {
        messageNode.innerHTML = 'Good attempt'
    } else if (percentageScore <= 0.8) {
        messageNode.innerHTML = 'Good job'
    } else if (percentageScore <= 0.95) {
        messageNode.innerHTML = 'Great work!'
    } else if (percentageScore <= 1) {
        messageNode.innerHTML = 'Amazing!'
    }

    showPage('end')
})