let startButton = document.getElementById('start-button')
let saveButton = document.querySelector('#end .save-btn')
let UNIQUE_ID = null

// get all pages
let pages = document.getElementsByClassName('page')

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
socket.on('end', () => {
    showPage('end')
})

socket.on('new student', (userIDs) => {
    let playerPageStudents = document.querySelector('#players-page').children
    let playerCount = document.querySelector('#connected-count')
    playerCount.innerHTML = userIDs.length

    for (studentBox of playerPageStudents) {
        if (studentBox.tagName.toLowerCase() === 'div') {
            if (userIDs.includes(parseInt(studentBox.dataset.userid))) {
                studentBox.classList.remove('unconnected')
            }
        }
    }
})

startButton.onclick = function() {
    let settingsForm = document.querySelector('#settings-page')
    let formData = new FormData(settingsForm)

    socket.emit('start', Object.fromEntries(formData))
}

saveButton.onclick = function() {
    console.log('saving quiz')
    socket.emit('save')
    window.location = '/'
}

// handling the pages on the initial start screen
var subPages = document.querySelector('.content').children
var topbarButtons = document.querySelector('.topbar > div').children

function showSubPage(pageId) {
    let page = document.getElementById(pageId)

    page.classList.remove('hide')
    for (let p of subPages) {
        if (p.id != pageId) {
            p.classList.add('hide')
        }
    }

    for (let button of topbarButtons) {
        if (button.dataset.pageid == pageId) {
            button.classList.add('active')
        } else {
            button.classList.remove('active')
        }
    }
}

for (let button of topbarButtons) {
    button.onclick = () => {
        showSubPage(button.dataset.pageid)
    }
}

showSubPage('settings-page')