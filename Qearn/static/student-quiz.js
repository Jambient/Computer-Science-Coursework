console.log('initialised')

let UNIQUE_ID = null

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

const socket = io.connect();

socket.on('connect',()=>{
    // get current room id
    let url_data = window.location.pathname.split("/")
    let roomID = parseInt(url_data[url_data.length - 1])

    // join the room on the server
    socket.emit("join", roomID)
})

socket.on('id', (id) => {
    console.log('got id')
    UNIQUE_ID = id
})

socket.on('run question', (data)=>{
    console.log('recieved run question')
    console.log(data)

    let currentTime = Date.now() / 1000
    let preQuestionTime = data['startTime']
    let duringQuestionTime = data['endTime']

    showPage('countdown')
    showAnswerType(data['questionData']['QuestionType'])
    let countDownPage = getPage('countdown')
    let preCountNum = countDownPage.querySelector('div h1')
    let duringCountNum = document.querySelector('.timer h1')

    let basicAnswerPage = getAnswerTypeElement('Basic')

    // set question page
    document.getElementById('current-question').innerHTML = `Question ${data['questionNumber']}`
    document.getElementById('question-total').innerHTML = `of ${data['maxQuestions']}`
    document.querySelector('.data-box h1').innerHTML = data['questionData']['QuestionString']

    basicAnswerPage.innerHTML = ''
    for (let answer of data['answerData']) {
        let button = document.createElement('button')
        button.innerHTML = answer['AnswerString']
        basicAnswerPage.appendChild(button)

        button.onclick = function() {
            socket.emit('answer', answer['ID'])
            console.log(answer['ID'])
            showPage('waiting')
        }
    }

    // the promise for the pre question timer
    new Promise((resolve, reject) => {
        var countInterval = setInterval(function() {
            if (preQuestionTime - currentTime <= 0) {
                clearInterval(countInterval)
                resolve()
            }
    
            currentTime = Date.now() / 1000
            let difference = Math.ceil(preQuestionTime - currentTime).toString();
            preCountNum.innerHTML = difference
        }, 200);
    }).then(() => {
        showPage('question')

        // the promise for the during question timer
        let currentTime = Date.now() / 1000
        new Promise((resolve, reject) => {
            var countInterval = setInterval(function() {
                if (duringQuestionTime - currentTime <= 0) {
                    clearInterval(countInterval)
                    resolve()
                }
        
                currentTime = Date.now() / 1000
                let difference = Math.max(Math.round(duringQuestionTime - currentTime), 0).toString();
                duringCountNum.innerHTML = difference
            }, 200);
        });
    });
})

socket.on('answer status', (isCorrect)=>{
    if (!(UNIQUE_ID in isCorrect)) {
        showPage('incorrect')
    } else {
        if (isCorrect[UNIQUE_ID]) {
            showPage('correct')
        } else {
            showPage('incorrect')
        }
    }
})