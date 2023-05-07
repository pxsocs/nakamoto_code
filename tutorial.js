function startTutorial(tutorialData) {
    // Wrap the content of the body in a new div
    $('body').children().not('script').wrapAll('<div class="blur-target"></div>');


    var currentIndex = 1;
    var totalPages = Object.keys(tutorialData).length;
    // blurBackground();
    showModal(tutorialData, currentIndex, totalPages);
    highlightComponent(tutorialData, currentIndex, totalPages);
    updateModal(tutorialData, currentIndex, totalPages);
}

function blurBackground() {
    $("body").addClass("blur");
}

function showModal(tutorialData, currentIndex, totalPages) {
    const modal = $('<div>').addClass('modal').attr('tabindex', '-1').attr('id', 'tutorial-modal');
    const modalDialog = $('<div>').addClass('modal-dialog modal-lg').css({ 'min-width': '90vw', 'min-height': '90vh' });
    const modalContent = $('<div>').addClass('modal-content').addClass('dark-modal');
    const modalHeader = $('<div>').addClass('modal-header').addClass('dark-modal');
    const closeModalButton = $('<button>').addClass('btn-close').attr('data-bs-dismiss', 'modal');
    closeModalButton.css('color', 'white');
    const modalBody = $('<div>').addClass('modal-body');
    const modalTitle = $('<h5>').addClass('modal-title').css('color', 'white').attr('id', 'modal-title');
    const modalInfo = $('<div>').attr('id', 'modal-info');
    const nextButton = $('<button>').addClass('btn btn-primary').attr('id', 'modal-next').text('Next');
    const prevButton = $('<button>').addClass('btn btn-secondary').attr('id', 'modal-prev').text('Previous');

    modalHeader.append(modalTitle);
    modalHeader.append(closeModalButton);
    modalBody.append(modalInfo);
    modalBody.append(prevButton, nextButton);
    modalContent.append(modalHeader, modalBody);
    modalDialog.append(modalContent);
    modal.append(modalDialog);
    $('body').append(modal);

    //
    modal.modal('show');

    // Event listeners for close, next, and previous buttons
    $("#modal-close").click(function () {
        closeTutorial();
    });

    // Close tutorial when clicking outside the modal content
    $("#tutorial-modal").click(function (event) {
        if (event.target.id === "tutorial-modal") {
            closeTutorial();
        }
    });

    $("#modal-next").click(function () {
        currentIndex = getNextIndex(tutorialData, currentIndex, totalPages);
        highlightComponent(tutorialData, currentIndex, totalPages);
        updateModal(tutorialData, currentIndex, totalPages);
    });

    $("#modal-prev").click(function () {
        currentIndex = getPreviousIndex(tutorialData, currentIndex, totalPages);
        highlightComponent(tutorialData, currentIndex, totalPages);
        updateModal(tutorialData, currentIndex, totalPages);
    });
}
function closeTutorial() {
    $('#tutorial-modal').remove();
    $('.highlight').removeClass('highlight');

    // Remove the 'blur' class from the body
    $('.blur-target').removeClass('blur');

    // Unwrap the content of the body from the blur-target div
    $('.blur-target').children().unwrap();
}
function highlightComponent(tutorialData, currentIndex, totalPages) {
    // Remove the 'blur' class from the body
    $('.blur-target').addClass('blur');

    // Remove the 'blur' class from the modal and the focused element
    $('#tutorial-modal, .highlight').removeClass('blur');

    // Remove the 'highlight' class from the previously highlighted element
    $(".highlight").removeClass("highlight");
    // Get the focused element using the 'focus-on' key from the data structure
    var focusedElement = $("#" + tutorialData[currentIndex]["focus-on"]);

    // Add the 'highlight' class to the focused element
    focusedElement.addClass("highlight");

    // Remove the 'blur' class from the focused element and its children
    focusedElement.removeClass('blur');
    focusedElement.find('*').removeClass('blur');
}

function updateModal(tutorialData, currentIndex, totalPages) {
    var currentData = tutorialData[currentIndex];
    $("#modal-title").html(currentData.title);
    $("#modal-info").html(currentData.info);
}

function getNextIndex(tutorialData, currentIndex, totalPages) {
    return currentIndex === totalPages ? 1 : currentIndex + 1;
}

function getPreviousIndex(tutorialData, currentIndex, totalPages) {
    return currentIndex === 1 ? totalPages : currentIndex - 1;
}
