// Variables
modalContainer = document.querySelector(".modal")
questionEditModal = document.querySelector(".modal .question-edit")
questionsPage = document.querySelector("#questions")
questionsContainer = questionsPage.querySelector('.created-questions')
questionLayout = questionsPage.querySelector('#question-layout')

// Functions
function addQuestion() {
    questionObject = questionLayout.cloneNode(true)
    questionObject.classList.remove('hide')

    questionObject.onclick = () => {
        console.log('button clicked ')
        modalContainer.classList.remove('hide')
        questionEditModal.classList.remove('hide')
    }

    questionsContainer.appendChild(questionObject)
}

addQuestion()
// What device forwards packets from one network to another? This is a very long question with extra words

// Connections