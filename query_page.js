$(document).ready(function () {
    $("#submit-query").click(function () {
        var query = $("#query-input").val();
        if (query.length === 0) {
            alert("Please enter a query.");
            return;
        }

        $.post("/query", { query: query }, function (data) {
            if (data.type === "text") {
                $("#query-response").html(data.response);
                $("#chart").empty();
            } else if (data.type === "chart") {
                $("#query-response").empty();
                drawChart(data.response);
            }
        });
    });
});

function drawChart(chartData) {
    var trace = {
        x: chartData.date,
        y: chartData.close,
        type: "scatter"
    };

    var data = [trace];
    var layout = {
        title: "BTC Close Prices",
        xaxis: { title: "Date" },
        yaxis: { title: "Close Price" }
    };

    Plotly.newPlot("chart", data, layout);
}
