let currentPageNumber = 0
let pages = document.getElementsByClassName('page')
let backButton = document.getElementById('back-button')
let pageProgress = document.getElementById('page-progress')
let formElement = document.querySelector('form')

let canSubmitForm = false

let emailPattern = /^\w+@[a-zA-Z_]+?\.[a-zA-Z]{2,3}$/;
let pageValidationFunctions = [
    function() {
        let radios = pages[0].querySelectorAll('input[type=radio]')
        console.log(radios)
        let isVerified = false
        for (let radio of radios) {
            if (radio.checked) {
                isVerified = true
            }
        }
        if (!isVerified) {
            toggleWarning(true, 'You must select one of the above options to continue')
        } else {
            toggleWarning(false)
        }
        return isVerified
    },
    async function() {
        let inputs = pages[1].querySelectorAll('input')
        console.log(inputs)
        let isVerified = true
        for (let input of inputs) {
            if (input.value.length == 0) {
                isVerified = false
                toggleWarning(true, 'You must fill in all the details to continue')
            } else if (input.type == 'email') {
                let result = input.value.match(emailPattern)
                if (result == null || result.length != 1) {
                    isVerified = false
                    toggleWarning(true, 'You must enter a valid email')
                }
            }
        }

        isEmailTaken = await checkEmailExistence(inputs[inputs.length-1].value)
        console.log(isEmailTaken)

        if (isEmailTaken) {
            toggleWarning(true, 'The email you have entered has already been taken')
            isVerified = false
        }

        if (isVerified) {
            toggleWarning(false)
        }

        return isVerified

    },
    function() {
        let inputs = pages[2].querySelectorAll('input')
        if (inputs[0].value.length < 8) {
            toggleWarning(true, 'Your password must be at least 8 characters')
            return false
        }
        if (!(/\d/.test(inputs[0].value))) {
            toggleWarning(true, 'Your password must contain a number')
            return false
        }
        if (inputs[0].value != inputs[1].value) {
            toggleWarning(true, 'Your confirmed password does not match')
            return false
        }
        toggleWarning(false)
        return true
    },
    async function(nowarnings) {
        let inputs = pages[3].querySelectorAll('input')
        let isVerified = true
        let fullSchoolCode = ""
        inputs[inputs.length-1].value = ""

        for (let input of inputs) {
            fullSchoolCode += input.value

            if (input.name != 'school-code' && input.value.length != 1) {
                if (!nowarnings) {
                    toggleWarning(true, 'You must enter the full code')
                }
                console.log('error on', input)
                isVerified = false
            }
        }
        console.log(fullSchoolCode)
        inputs[inputs.length-1].value = fullSchoolCode

        // check if school code exists
        doesSchoolExist = await checkSchoolExistence(fullSchoolCode)
        console.log(doesSchoolExist)

        if (!doesSchoolExist) {
            toggleWarning(true, 'The school code you have entered is not valid')
            isVerified = false
        }

        if (isVerified && !nowarnings) {
            toggleWarning(false)
        }

        canSubmitForm = isVerified

        return isVerified
    }
]

async function checkEmailExistence(email) {
    return fetch('api/accounts/email/' + email)
        .then((response)=>response.text())
        .then((data)=>{
            if (data == 'True') {
                return true
            } else {
                return false
            }
        });
}

async function checkSchoolExistence(code) {
    if (code.length == 0) {
        return false
    }
    return fetch('api/schools/' + code)
        .then((response)=>response.text())
        .then((data)=>{
            if (data == 'True') {
                return true
            } else {
                return false
            }
        });
}

function toggleWarning(bool, message) {
    let currentPage = pages[currentPageNumber]
    let warningElement = currentPage.querySelector('.warning')

    if (bool) {
        warningElement.innerHTML = message
        warningElement.classList.remove('hide')
    } else {
        warningElement.classList.add('hide')
    }
}

function updatePages() {
    // show the current page and hide the rest
    for (let page of pages) {
        page.classList.add('hide')
    }
    pages[currentPageNumber].classList.remove('hide')

    // make sure the back button is hidden on the first page
    if (currentPageNumber > 0) {
        backButton.classList.remove('hide')
    } else {
        backButton.classList.add('hide')
    }

    // update the page progress bar
    for (let i = 0; i < pageProgress.children.length; i++) {
        let bar = pageProgress.children[i]
        if (i <= currentPageNumber) {
            bar.classList.add('active')
        } else {
            bar.classList.remove('active')
        }
    }
}

updatePages()

for (let page of pages) {
    button = page.querySelector('button')
    
    button.onclick = async function() {
        let isPageValidated = await pageValidationFunctions[currentPageNumber]()
        console.log('final', isPageValidated, currentPageNumber)

        if (isPageValidated) {
            currentPageNumber = Math.min(pages.length-1, currentPageNumber + 1)
            updatePages()
        }
    }
}

// focus next input field code for school code page
let codeInputs = pages[pages.length-1].querySelectorAll('input[size="1"]')
console.log(codeInputs)
codeInputs.forEach(el => el.onkeyup = e => e.target.value && el.nextElementSibling.focus())

// back button code
backButton.onclick = function() {
    currentPageNumber = Math.max(0, currentPageNumber - 1)
    updatePages()
}

formElement.onsubmit = function() {
    console.log('submitting')

    if (canSubmitForm) {
        return true
    } else {
        return false
    }

    // let isPageValidated = await pageValidationFunctions[pages.length-1](true)

    // if (!isPageValidated) {
    //     console.log('cannot submit')
    //     return false;
    // }
    return false;
    //return true
}