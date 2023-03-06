// Variables
questionEditModal = document.querySelector(".modal .question-edit")
questionsPage = document.querySelector("#questions")
questionsContainer = questionsPage.querySelector('.questions')
questionLayout = questionsPage.querySelector('#question-layout')

// Functions
function addQuestion() {
    questionObject = questionLayout.cloneNode(true)
    questionObject.classList.remove('hide')
    questionsContainer.appendChild(questionObject)
}

// Connections