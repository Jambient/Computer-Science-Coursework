
area = window.location.pathname.split("/")

var sidebar = document.getElementsByClassName('sidebar')[0]

Array.prototype.forEach.call(
	document.querySelectorAll('.option'),
	function (element) {
		if (element.classList.contains('option')) {
			element.onclick = clickedOption;
			if (element.dataset.area == area[1]) {
				element.classList.add('active')
				var selected = element.getElementsByClassName('selected')[0]
				selected.style.cssText = "display: block;"
			}
		}
	}
);

function clickedOption(element) {
	element = this;

	window.location.href = "/" + element.dataset.area;

	// sidebarChildren.forEach((item) => {
	// 	item.classList.remove('active')
	// });

	// element.classList.add('active')
}

// new classroom button
var newClassroom = document.getElementById('new-class-button')
var modal = document.getElementById('modal')

newClassroom.onclick = function (element) {
	element = this;
	console.log('clicked new classroom button')
	modal.classList.remove('hide')
}