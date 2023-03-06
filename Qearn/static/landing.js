window.onscroll = function() {handleScrolling()};
const navBar = document.querySelector('nav')

function handleScrolling() {
    if (document.body.scrollTop > 50 || document.documentElement.scrollTop > 50) {
        navBar.classList.add("scrolled")
    } else {
        navBar.classList.remove("scrolled")
    }
}