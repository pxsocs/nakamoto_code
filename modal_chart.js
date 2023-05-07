$(document).ready(function () {
    let currentSymbol;
    const modal = $('<div>').addClass('modal').attr('tabindex', '-1').attr('id', 'chartModal');
    const modalDialog = $('<div>').addClass('modal-dialog modal-lg').css({ 'min-width': '90vw', 'min-height': '90vh' });
    const modalContent = $('<div>').addClass('modal-content').addClass('dark-modal');
    const modalHeader = $('<div>').addClass('modal-header').addClass('dark-modal');;
    const closeModalButton = $('<button>').addClass('btn-close').attr('data-bs-dismiss', 'modal');
    closeModalButton.css('color', 'white');
    const modalBody = $('<div>').addClass('modal-body');
    const spinner = $('<div>').addClass('spinner-border').attr('id', 'spinnerLoad').css('width', '3rem').css('height', '3rem');
    const chartContainer = $('<div>').attr('id', 'chartContainer').css('min-height', '70vh');
    const btnGroup = $('<div>').addClass('btn-group');
    const btnHistoricalChart = $('<button>').addClass('btn btn-secondary active').text('Historical Chart');
    const btnInfo = $('<button>').addClass('btn btn-secondary').text('Info');
    const btnHistogram = $('<button>').addClass('btn btn-secondary').text('Histogram');
    btnGroup.append(btnHistoricalChart, btnInfo, btnHistogram);
    const modalTitle = $('<h5>').addClass('modal-title').css('color', 'white').attr('id', 'modalTitle');

    const inputGroup = $('<div>').addClass('input-group input-group-sm mt-2').attr('id', 'days_input');;
    const inputGroupPrepend = $('<div>').addClass('input-group-prepend');
    const inputGroupText = $('<span>').addClass('input-group-text').text('Group data in how many days?');
    const inputField = $('<input>').attr('type', 'number').addClass('form-control').val('30');

    inputGroupPrepend.append(inputGroupText);
    inputGroup.append(inputGroupPrepend);
    inputGroup.append(inputField);
    modalBody.append(inputGroup);


    modalTitle.append(btnGroup);
    modalHeader.append(modalTitle);
    modalHeader.append(closeModalButton);
    modalBody.append(spinner);
    const infoContainer = $('<div>').attr('id', 'infoContainer').css('display', 'none');
    modalBody.append(infoContainer);
    modalContent.append(modalHeader, modalBody);
    modalDialog.append(modalContent);
    modal.append(modalDialog);
    modalBody.append(chartContainer);

    $('body').append(modal);



    let chartOptions; // Add this line to store chart options
    $('[data-chart-symbol]').on('click', function () {
        reset_modal();
        const symbol = $(this).data('chart-symbol');
        currentSymbol = $(this).data('chart-symbol');
        chartOptions = $(this).data('chart-options'); // Change this line to store chart options in the variable
        modal.modal('show');
        spinner.show();
        chartContainer.hide();
        loadChartData(symbol, chartOptions);
    });

    // Listeners / Handlers
    btnHistoricalChart.on('click', function () {
        reset_modal();
        // Set this button as active, and the others as inactive
        btnHistoricalChart.addClass('active');
        btnInfo.removeClass('active');
        btnHistogram.removeClass('active');
        // Reload Data
        loadChartData(currentSymbol, chartOptions); // Use currentSymbol and chartOptions here
    });


    btnInfo.on('click', function () {
        reset_modal();

        // Set this button as active, and the others as inactive
        btnInfo.addClass('active');
        btnHistoricalChart.removeClass('active');
        btnHistogram.removeClass('active');

        // Display Table
        $('#infoContainer').show();
    });


    btnHistogram.on('click', function () {
        reset_modal();
        $('#days_input').show();
        // Set this button as active, and the others as inactive
        btnHistogram.addClass('active');
        btnHistoricalChart.removeClass('active');
        btnInfo.removeClass('active');

        spinner.show();
        const frequency_days = inputField.val();
        loadHistogramData(currentSymbol, frequency_days);
    });



    inputField.on('input', function () {
        const frequency_days = $(this).val();
        if (frequency_days > 0) {
            $('.table-responsive').hide();
            $('#chartContainer').hide();
            spinner.show();
            loadHistogramData(currentSymbol, frequency_days);
        }
    });


    $(document).on('click', function (e) {
        if ($(e.target).hasClass('modal')) {
            modal.modal('hide');
        }
    });
});


// Hide and deselect buttons
function reset_modal() {
    $('#days_input').hide();
    $('.table-responsive').hide();
    $('#chartContainer').hide();
    $('#infoContainer').hide();
}

function loadChartData(symbol, chartOptions) {
    $.ajax({
        url: `/historical_data?ticker=${symbol}&df=true&format=json`,
        method: 'GET',
        dataType: 'json',
        success: function (data) {
            $('#spinnerLoad').hide()
            if (data.empty) {
                $('#chartContainer').text('This ticker was not found.');
            } else {
                createChart_modal(data, chartOptions);
                createInfoTable(data);
            }
        },
        complete: function () {
            $('#spinnerLoad').hide()
            $('#chartContainer').show();
        },
    });
}

function createInfoTable(data) {
    const infoData = data.ticker_info[0];

    const table = $('<table>').addClass('table table-dark table-striped table-hover');
    const tbody = $('<tbody>');

    const rows = [
        { key: 'Currency', value: infoData.fx },
        { key: 'Name', value: infoData.name },
        { key: 'Notes', value: infoData.notes },
        { key: 'Provider', value: infoData.provider },
        { key: 'Source Ticker', value: infoData.src_ticker },
        { key: 'Symbol', value: infoData.symbol },
        { key: 'First Date', value: formatDateString(data.first_date) },
        { key: 'Latest Date', value: formatDateString(data.latest_date) },
        { key: 'Latest Price', value: formatNumber(data.latest_price, 2) },
        { key: 'Number of Days', value: data.num_days },
        { key: 'Source', value: data.source },
        { key: 'Source URL', value: data.source_url },
    ];


    rows.forEach(({ key, value }) => {
        const tr = $('<tr>');
        const th = $('<th>').text(key);
        const td = $('<td class="text-end">').text(value);
        tr.append(th, td);
        tbody.append(tr);
    });

    table.append(tbody);
    $('#infoContainer').html(table);
}



function appendScriptIfNotExist(src) {
    // Check if the script already exists in the document head
    const existingScript = document.head.querySelector(`script[src="${src}"]`);

    // If the script doesn't exist, create and append it
    if (!existingScript) {
        const script = document.createElement('script');
        script.src = src;
        document.head.appendChild(script);
    }
}


function createChart_modal(data, chartOptions) {

    let parsedData;

    try {
        parsedData = JSON.parse(data.df); // Parse the entire DataFrame JSON string
        chartData = Object.entries(parsedData.close_converted).map(([key, value]) => [
            parseInt(key),
            value,
        ]);
        tickerInfo = data.ticker_info[0];
    } catch (error) {
        $('#chartContainer').html('This ticker returned an error: ' + error + '.');

        $('#chartContainer').show();
        $('.spinner-border').hide();

        console.error('Invalid JSON data:', data.df);
        return;
    }

    const latestDataPoint = chartData[chartData.length - 1];

    const latestDate = latestDataPoint[0];
    const latestValue = latestDataPoint[1];

    const modalChart = Highcharts.stockChart('chartContainer', {
        chart: {
            backgroundColor: 'transparent',
            zoomType: 'xy',
            events: {
                load: function () {
                    this.renderer.image('/static/images/swan-icon-snow.png',
                        this.chartWidth / 2 - 100, // Center the image horizontally
                        this.chartHeight / 2 - 95, // Center the image vertically
                        300, 260 // Maintain original aspect ratio
                    ).css({
                        opacity: 0.1 // Increase opacity for visibility in dark mode
                    }).add();
                }
            },
        },
        title: {
            text: `${tickerInfo.name} (${tickerInfo.symbol})`,
            style: {
                color: '#C0C0C0'
            }
        },
        subtitle: {
            useHTML: true,
            text: `From ${formatDateString(data.first_date)} to ${formatDateString(data.latest_date)}<br>Source: <a href="${data.source_url}" target="_blank">${data.source}</a>`,
        },
        credits: {
            enabled: false,
        },
        plotOptions: {
            series: {
                dataGrouping: {
                    enabled: false,
                },
                dataLabels: {
                    enabled: false
                },
            },
        },
        series: [
            {
                name: tickerInfo.symbol,
                data: chartData,
            },
        ],

        xAxis: {
            type: 'datetime',
            gridLineWidth: 0.5,
            gridLineColor: '#1111111',
            labels: {
                style: {
                    color: 'white',
                },
            },
        },
        yAxis: {
            gridLineWidth: 0.5,
            gridLineColor: '#1111111',
            labels: {
                style: {
                    color: 'white',
                },
            },
        },
        navigator: {
            enabled: false,
        },
        rangeSelector: {
            buttons: [
                {
                    type: 'month',
                    count: 1,
                    text: '1m',
                },
                {
                    type: 'month',
                    count: 3,
                    text: '3m',
                },
                {
                    type: 'month',
                    count: 6,
                    text: '6m',
                },
                {
                    type: 'ytd',
                    text: 'YTD',
                },
                {
                    type: 'year',
                    count: 1,
                    text: '1y',
                },
                {
                    type: 'all',
                    text: 'All',
                },
            ],
            selected: 4,
            inputStyle: {
                color: 'white',
            },
            buttonTheme: {
                fill: 'none',
                stroke: 'none',
                'stroke-width': 0,
                r: 0,
                style: {
                    color: 'white',
                },
                states: {
                    hover: {
                        fill: 'white',
                        style: {
                            color: 'black',
                        },
                    },
                    select: {
                        fill: 'white',
                        style: {
                            color: 'black',
                        },
                    },
                },
            },
        },

        scrollbar: {
            barBackgroundColor: 'white',
            barBorderRadius: 7,
            barBorderWidth: 0,
            buttonBackgroundColor: 'white',
            buttonBorderWidth: 0,
            buttonArrowColor: 'black',
            buttonBorderRadius: 7,
            rifleColor: 'black',
            trackBackgroundColor: 'gray',
            trackBorderWidth: 1,
            trackBorderColor: 'silver',
            trackBorderRadius: 7,
        },

        legend: {
            enabled: false,
        },

        credits: {
            enabled: false,
        },
        yAxis: {
            labels: {
                style: {
                    color: 'white',
                },
            },
        },

        tooltip: {
            formatter: function () {
                return formatNumber(this.y, 2);
            },
        },

        navigator: {
            series: {
                color: 'white',
            },
        },

        rangeSelector: {
            buttons: [
                {
                    type: 'month',
                    count: 1,
                    text: '1m',
                },
                {
                    type: 'month',
                    count: 3,
                    text: '3m',
                },
                {
                    type: 'month',
                    count: 6,
                    text: '6m',
                },
                {
                    type: 'ytd',
                    text: 'YTD',
                },
                {
                    type: 'year',
                    count: 1,
                    text: '1y',
                },
                {
                    type: 'all',
                    text: 'All',
                },
            ],
            selected: -1,
            inputStyle: {
                color: 'white',
            },
            buttonTheme: {
                fill: 'none',
                stroke: 'none',
                'stroke-width': 0,
                r: 0,
                style: {
                    color: 'white',
                },
                states: {
                    hover: {
                        fill: 'white',
                        style: {
                            color: 'black',
                        },
                    },
                    select: {
                        fill: 'white',
                        style: {
                            color: 'black',
                        },
                    },
                },
            },
        },

        legend: {
            enabled: false,
        },

        credits: {
            enabled: false,
        },

    });

    // Update the chart with the chartOptions object
    // ex: data-chart-options='{"title": {"text": "text"}}'
    if (chartOptions) {
        modalChart.update(chartOptions);
    }
}


function loadHistogramData(symbol, frequency_days) {

    $.ajax({
        url: base_url() + `api/histogram?ticker=${symbol}&frequency_days=${frequency_days}`,
        method: 'GET',
        dataType: 'json',
        success: function (data) {
            $('#spinnerLoad').hide()
            createHistogramChart(data, frequency_days);

        },
        complete: function () {
            $('#spinnerLoad').hide()
            $('#chartContainer').show();
        },
    });
}

function createHistogramChart(data, days) {

    data = JSON.parse(data);

    // Convert the data object to an array
    const dataArray = Object.values(data);

    // Now you can use the .map() function on dataArray
    const chartData = dataArray.map(item => {
        if (item && item.bin_range) {
            return {
                x: item.bin_range.mid,
                y: item.count
            };
        }
    }).filter(item => item !== undefined);


    const histogramChart = Highcharts.chart('chartContainer', {
        chart: {
            type: 'column',
            data: {
                labels: chartData.map(d => d.bin_range),
            },
            backgroundColor: 'transparent',
        },
        title: {
            text: `${days}-Day Returns Histogram`,
            style: {
                color: '#C0C0C0'
            }
        },
        xAxis: {
            labels: chartData.map(d => formatNumber(d.return * 100, 2) + "%"),
            ticks: {
                color: 'white'
            },
            labels: {
                style: {
                    color: 'white',
                },
                formatter: function () {
                    return formatNumber(this.value * 100, 2) + "%";
                }
            },
            grid: {
                color: 'white'
            },
            barPercentage: 0.85, // Adjust this value (e.g., 0.8) to control the width of the bars
            categoryPercentage: 1.0 // Adjust this value (e.g., 1.0) to control the space between the bars
        },
        yAxis: {
            gridLineWidth: 0.5,
            gridLineColor: 'darkgray',
            labels: {
                style: {
                    color: 'white',
                },
            },
            title: {
                text: 'Frequency',
                style: {
                    color: 'white',
                },
            },
        },
        legend: {
            enabled: false,
        },
        credits: {
            enabled: false,
        },
        tooltip: {
            headerFormat: '',
            pointFormat: 'Return: {point.x:.2f}<br>Frequency: {point.y}',
        },
        series: [
            {
                name: 'Frequency',
                data: chartData,
            },
        ],
    });
}
