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

startButton.onclick = function() {
    console.log('epic')
    socket.emit('start')
}

saveButton.onclick = function() {
    console.log('saving quiz')
    socket.emit('save')
}