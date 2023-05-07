$(document).ready(function () {
    $(".show-at-load").addClass("highlight");
    setTimeout(function () {
        $(".show-at-load").removeClass("highlight");
    }, 2000);
});
