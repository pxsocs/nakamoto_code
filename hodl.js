$(document).ready(function () {
    console.log("00000080   01 04 45 54 68 65 20 54  69 6D 65 73 20 30 33 2F   ..EThe Times 03/");
    console.log("00000090   4A 61 6E 2F 32 30 30 39  20 43 68 61 6E 63 65 6C   Jan/2009 Chancel");
    console.log("000000A0   6C 6F 72 20 6F 6E 20 62  72 69 6E 6B 20 6F 66 20   lor on brink of ");
    console.log("000000B0   73 65 63 6F 6E 64 20 62  61 69 6C 6F 75 74 20 66   second bailout f");
    console.log("000000C0   6F 72 20 62 61 6E 6B 73  FF FF FF FF 01 00 F2 05   or banksÿÿÿÿ..ò.");

    $body = $("body");

    // This page doesn't look too good in Dark Mode
    const toggle = $("#darkModeToggle");
    const body = $("body");
    body.toggleClass("dark-mode");
    $('#darkModeform').hide();

    window.btcPrice = 0;
    window.data = null;

    // Check landscape or portrait
    // Update orientation when the page is loaded
    updateOrientation();

    // Update orientation when the device is rotated or the window is resized
    window.addEventListener('orientationchange', updateOrientation);
    window.addEventListener('resize', updateOrientation);

    // Call adjustFontSize on page load
    adjustFontSize();

    // Call adjustFontSize when the window is resized
    $(window).resize(adjustFontSize);

    $(document).on({
        ajaxStart: function () { $body.addClass("loading"); },
        ajaxStop: function () { $body.removeClass("loading"); }
    });

    // Store these
    window.frequency = $('#frequency').val();
    window.period_exclude = $('#period_exclude').val();

    retrieve_data();

    // Listen for changes but wait 2 sec before triggering
    let retrieveDataTimeout;
    function triggerRetrieveData() {
        clearTimeout(retrieveDataTimeout);

        retrieveDataTimeout = setTimeout(function () {
            retrieve_data();
        }, 2000); // 2000 milliseconds (2 seconds) delay
    }
    // Trigger the retrieve_data function when any of the specified elements change
    $('#ticker, #start_date, #end_date, #frequency, #period_exclude').on('change', triggerRetrieveData);

});


function retrieve_data(start_date = null, end_date = null, frequency = null, period_exclude = null, justData = false) {

    // if none are provided, get the one at the table
    start_date = start_date || $('#start_date').val();
    end_date = end_date || $('#end_date').val();
    frequency = frequency || $('#frequency').val();
    period_exclude = period_exclude || $('#period_exclude').val();

    var ticker = $('#ticker').val()
    var fx = "USD"

    $('#error_message').html('<div class="alert alert-primary" role = "alert"> Loading Data.Please Wait...</div >');

    button_code = '<button type="button" class="btn btn-dark" style="display: none;">Show More</button>';

    $.ajax({
        type: "GET",
        dataType: 'json',
        url: "/hodl_analysis/stats_json?ticker=" + ticker + "&force=False&fx=" + fx + "&start_date=" + start_date + "&end_date=" + end_date + "&frequency=" + frequency + "&period_exclude=" + period_exclude,
        error: function (request, status, error) {
            $('#error_message').html('<div class="alert alert-danger" role = "alert"> Something went wrong. Try again.</div >');
            console.log(request.error);
            console.log(status);
            console.log(error);

        },
        success: function (data) {
            if (data.status == "error") {
                $('#error_message').html('<div class="alert alert-danger" role = "alert"> Something went wrong. Try again.</div >');
            } else {
                if (justData == true) {
                    return data;
                } else {
                    $('#error_message').html(" ");
                    window.data = data
                    $('#nlargest').html(data.nlargest).append(button_code);
                    $('#nsmallest').html(data.nsmallest).append(button_code);
                    updateShowMoreLess();
                    createTotalRankChart(data);
                }
            }
        }
    });

};

function createTotalRankChart(data) {
    let dataSets = [];

    $('div.returns').each(function (index) {
        let smallData = [];
        let largeData = [];

        // Extract data from the 'smallest' table within the current 'returns' div
        $(this).find('table.smallest tbody tr').each(function () {
            let returnPercentage = $(this).find('td:nth-child(5)').text();
            let returnVal = parseFloat(returnPercentage) / 100;
            smallData.push(returnVal);
        });

        // Extract data from the 'largest' table within the current 'returns' div
        $(this).find('table.largest tbody tr').each(function () {
            let returnPercentage = $(this).find('td:nth-child(5)').text();
            let returnVal = parseFloat(returnPercentage) / 100;
            largeData.push(returnVal);
        });

        dataSets.push({ smallData, largeData });

        // Create a div to hold the chart
        const chartDivId = `total_rank_chart_${index}`;
        const chartDiv = $('<div>').attr('id', chartDivId);
        $(this).find(".chart_placeholder").append(chartDiv);

        // Create dynamic categories
        const categories = smallData.map((_, i) => i + 1);

        createResultsTable(data);

        // Create a chart with the extracted data
        Highcharts.chart(chartDivId, {
            chart: {
                events: {
                    load: function () {
                        this.renderer.image('/static/images/swan-logo-primary.png',
                            this.chartWidth / 2 - 125,
                            this.chartHeight / 2 - 45,
                            250, 90
                        ).css({
                            opacity: 0.3
                        }).attr({
                            zIndex: 10
                        }).add();
                    },
                },
                backgroundColor: 'transparent',
                type: 'bar',
            },
            credits: {
                enabled: false,
            },
            title: {
                text: 'Ranking of Returns<br>',
            },
            subtitle: {
                text: data.start_date + ' to ' + data.end_date,
            },
            xAxis: {
                categories: categories,
                labels: {
                    enabled: false
                },
            },
            yAxis: {
                // Min tick starts at -1
                title: {
                    text: 'Returns',
                },
                labels: {
                    formatter: function () {
                        return (this.value * 100).toFixed(2) + '%';
                    },
                },
            },
            plotOptions: {
                series: {
                    dataLabels: {
                        enabled: true,
                        formatter: function () {
                            return (this.point.y * 100).toFixed(2) + '%';
                        },
                        align: 'center',
                        inside: true,
                    },
                    grouping: false,
                    pointPadding: 0,
                    groupPadding: 0,
                },
            },
            series: [
                {
                    name: 'Smallest Returns',
                    data: smallData,
                    color: '#ED8C8C',
                    pointPadding: 0.1,
                    dataLabels: {
                        x: -5,
                    },

                },
                {
                    name: 'Largest Returns',
                    data: largeData,
                    color: '#5fba7d',
                    pointPadding: 0.1,
                    dataLabels: {
                        x: 5,
                    },
                },
            ],
        });

    });

}


function createResultsTable(data) {
    $('div.returns').each(function (index) {
        // Create the results table
        const table = $('<table class="table table-condensed table-striped">');
        const thead = $('<thead>');
        const tbody = $('<tbody>');

        // Create the header row
        const headerRow = $("<tr class='text-center'>");
        headerRow.append($('<th>').text(''));
        headerRow.append($('<th>').text('Smallest Returns'));
        headerRow.append($('<th>').text('Largest Returns'));
        headerRow.append($('<th>').text('Both'));
        thead.append(headerRow);

        // Create the data rows
        const meanRow = $('<tr>');
        meanRow.append($('<td>').text('Mean'));
        meanRow.append($("<td class='text-center'>").text(formatNumber(data['nsmallest_mean'] * 100, 2, '', '%')));
        meanRow.append($("<td class='text-center'>").text(formatNumber(data['nlargest_mean'] * 100, 2, '', '%')));
        meanRow.append($("<td class='text-center'>").text(formatNumber(parseFloat(data['nsmallest_mean']) * 100 + parseFloat(data['nlargest_mean']) * 100, 2, '', '%')));
        tbody.append(meanRow);

        const totalReturnRow = $('<tr>');
        totalReturnRow.append($('<td>').text('Total Return'));
        totalReturnRow.append($("<td class='text-center'>").text(formatNumber(data['nsmallest_tr'] * 100, 2, '', '%')));
        totalReturnRow.append($("<td class='text-center'>").text(formatNumber(data['nlargest_tr'] * 100, 2, '', '%')));
        totalReturnRow.append($("<td class='text-center'>").text(formatNumber(data['nboth_tr'] * 100, 2, '', '%')));
        tbody.append(totalReturnRow);

        table.append(thead);
        table.append(tbody);


        // Append the table below the chart
        $(this).find(".table_placeholder").html(table);

        // Create the additional data table
        table_2 = '<table class="table table-condensed table-striped" style="width: 50%">';
        table_2 += '<thead>';
        table_2 += '<tbody>';
        table_2 += '<tr>';
        table_2 += '<td>Starting Value</td>';
        table_2 += `<td class="text-end">${formatNumber(data['ticker_start_value'], 0)}</td>`;
        table_2 += '</tr>';
        table_2 += '<tr>';
        table_2 += '<td>Final Value</td>';
        table_2 += `<td class="text-end">${formatNumber(data['ticker_end_value'], 0)}</td>`;
        table_2 += '</tr>';
        table_2 += '<tr>';
        table_2 += '<td>Total Return in Period</td>';
        table_2 += `<td class="text-end">${formatNumber(data['period_tr'] * 100, 2, '', '%')}</td>`;
        table_2 += '</tr>';
        table_2 += '<tr>';
        table_2 += '<td>Period excluding largest</td>';
        table_2 += `<td class="text-end">${formatNumber(data['exclude_nlargest_tr'] * 100, 2, '', '%')}</td>`;
        table_2 += '</tr>';
        table_2 += '<tr>';
        table_2 += '<td>Period excluding smallest</td>';
        table_2 += `<td class="text-end">${formatNumber(data['exclude_nsmallest_tr'] * 100, 2, '', '%')}</td>`;
        table_2 += '</tr>';
        table_2 += '</tbody>';
        table_2 += '</table>';




        // Append the additional data below the table
        $(this).find(".table_placeholder").append(table_2);
    });
}

function updateShowMoreLess() {
    $('.returns_table').each(function () {
        const $table = $(this).find('table');
        const $rows = $table.find('tbody tr');
        const $showMoreLessBtn = $(this).next('.show-more-less');

        if ($rows.length > 10) {
            $rows.slice(10).addClass('hide-row');
            $showMoreLessBtn.show();
        } else {
            $showMoreLessBtn.hide();
        }

        $showMoreLessBtn.off('click').on('click', function () {
            if ($showMoreLessBtn.text() === 'SHOW MORE') {
                $rows.removeClass('hide-row');
                $showMoreLessBtn.text('SHOW LESS');
            } else {
                $rows.slice(10).addClass('hide-row');
                $showMoreLessBtn.text('SHOW MORE');
            }
        });
    });
}


