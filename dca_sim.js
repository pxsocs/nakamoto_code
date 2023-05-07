$(document).ready(function () {

    window.btcPrice = 0;

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

    const btc_coins = 20999999.9769

    createCharts(chartData);

    fetch("/realtime_btc")
        .then((response) => response.json())
        .then((data) => {
            window.btcPrice = data.btc_usd;
        });

    $('#ticker, #capital, #frequency, #start_date, #end_date, #upfront_percent, #allocation_periods')
        .on('change keyup', onInputChange);

});


function buildURL() {
    const baseURL = '/apps/dca_sim';
    const ticker = $('#ticker').val();
    const capital = parseFloat($('#capital').val().replace(/,/g, ''));
    const frequency = $('#frequency').val();
    const start_date = $('#start_date').val();
    const end_date = $('#end_date').val();
    const upfront_percent = parseFloat($('#upfront_percent').val().replace('%', '')) / 100;
    const allocation_periods = $('#allocation_periods').val();

    const url = `${baseURL}?ticker=${ticker}&capital=${capital}&frequency=${frequency}&start_date=${start_date}&end_date=${end_date}&upfront_percent=${upfront_percent}&allocation_periods=${allocation_periods}`;
    return url;
}

let inputChangeTimeout;

function onInputChange() {
    clearTimeout(inputChangeTimeout);
    inputChangeTimeout = setTimeout(() => {
        window.location.href = buildURL();
    }, 2000);
}


function createCharts(chartDataJson) {
    dates = chartDataJson.date;
    const chartData = chartDataJson;

    const chartOptions = {
        chart: {
            events: {
                load: function () {
                    this.renderer.image('/static/images/swan-icon-snow.png',
                        this.chartWidth / 2 - 100, // Center the image horizontally
                        this.chartHeight / 2 - 95, // Center the image vertically
                        250, 240 // Maintain original aspect ratio
                    ).css({
                        opacity: 0.1 // Increase opacity for visibility in dark mode
                    }).add();
                }
            },
            backgroundColor: 'transparent'
        },
        legend: {
            enabled: false,
            style: {
                color: '#FFFFFF'
            }
        },
        credits: {
            enabled: false,
        },
        xAxis: {
            type: 'datetime',
            labels: {
                formatter: function () {
                    return Highcharts.dateFormat('%Y-%m-%d', this.value);
                },
                style: {
                    color: '#FFFFFF'
                }
            },
        },
        yAxis: {
            labels: {
                style: {
                    color: '#FFFFFF'
                }
            },
        },
    };


    // Filter the dates and allocation arrays to remove elements with zero allocations
    const filteredDates = dates.filter((_, index) => chartData.allocation[index] !== 0);
    const filteredAllocations = chartData.allocation.filter(value => value !== 0);



    // Chart 4: Normalized close vs. normalized portfolio position
    Highcharts.chart('chart4', Highcharts.merge(chartOptions, {
        title: {
            text: 'Performance of strategy<br>compared to ' + window.params['ticker'],
            style: {
                color: '#FFFFFF'
            }
        },
        xAxis: {
            type: 'datetime',
            labels: {
                formatter: function () {
                    return Highcharts.dateFormat('%Y-%m-%d', this.value);
                },
            },
        },
        yAxis: {
            title: {
                text: 'Normalized Value (Base 100)'
            }
        },
        series: [{
            name: 'Lump Sum Strategy (asset performance)',
            data: chartData.normalized_close.map((value, index) => [dates[index], value]),
            color: '#fd7e14',
            dataLabels: {
                enabled: true,
                formatter: function () {
                    if (this.point.index === this.series.data.length - 1) {
                        return ` Lumpsum Final Value: $${formatNumber(this.y, 2)} ►&nbsp;&nbsp;&nbsp;`;
                    } return null;
                },
                style: {
                    font: 'normal 14px "Roboto", arial',
                    fontWeight: 'strong',
                    fontSize: '14px',
                    color: 'white',
                },
                y: 10,
                backgroundColor: 'transparent',
                padding: 5
            },
        }, {
            name: 'Cost Averaging Strategy',
            data: chartData.normalized_port_position.map((value, index) => [dates[index], value]),
            color: '#FFFFFF',
            dataLabels: {
                enabled: true,
                formatter: function () {
                    if (this.point.index === this.series.data.length - 1) {
                        return ` Strategy Final Value: $${formatNumber(this.y, 2)} ►&nbsp;&nbsp;&nbsp;`;
                    }
                    return null;
                },
                style: {
                    font: 'normal 14px "Roboto", arial',
                    fontWeight: 'strong',
                    fontSize: '14px',
                    color: 'white',
                },
                y: 10,
                backgroundColor: 'transparent',
                padding: 5
            },
        }]
    }));
};
