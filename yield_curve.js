var yieldData = [];

function oneMonthAgo() {
    const currentDate = new Date();
    currentDate.setMonth(currentDate.getMonth() - 1);
    return currentDate.toISOString().slice(0, 10);
}

function threeMonthsAgo() {
    const currentDate = new Date();
    currentDate.setMonth(currentDate.getMonth() - 3);
    return currentDate.toISOString().slice(0, 10);
}

function sixMonthsAgo() {
    const currentDate = new Date();
    currentDate.setMonth(currentDate.getMonth() - 6);
    return currentDate.toISOString().slice(0, 10);
}

function twelveMonthsAgo() {
    const currentDate = new Date();
    currentDate.setMonth(currentDate.getMonth() - 12);
    return currentDate.toISOString().slice(0, 10);
}

function fetchData(url) {
    return new Promise((resolve, reject) => {
        $.ajax({
            url: url,
            type: 'GET',
            success: function (data) {
                resolve(data);
            },
            error: function (error) {
                reject(error);
            },
        });
    });
}

$(document).ready(async function () {
    const latestUrl = '/api/yield_curve?issuer=US Treasury&date=latest';
    const oneMonthAgoUrl = `/api/yield_curve?issuer=US Treasury&date=${oneMonthAgo()}`;
    const threeMonthsAgoUrl = `/api/yield_curve?issuer=US Treasury&date=${threeMonthsAgo()}`;
    const sixMonthsAgoUrl = `/api/yield_curve?issuer=US Treasury&date=${sixMonthsAgo()}`;
    const twelveMonthsAgoUrl = `/api/yield_curve?issuer=US Treasury&date=${twelveMonthsAgo()}`;

    try {
        const [latestData, oneMonthAgoData, threeMonthsAgoData, sixMonthsAgoData, twelveMonthsAgoData] = await Promise.all([
            fetchData(latestUrl),
            fetchData(oneMonthAgoUrl),
            fetchData(threeMonthsAgoUrl),
            fetchData(sixMonthsAgoUrl),
            fetchData(twelveMonthsAgoUrl),
        ]);

        const latestYields = processYieldData(latestData);
        const oneMonthAgoYields = processYieldData(oneMonthAgoData);
        const threeMonthsAgoYields = processYieldData(threeMonthsAgoData);
        const sixMonthsAgoYields = processYieldData(sixMonthsAgoData);
        const twelveMonthsAgoYields = processYieldData(twelveMonthsAgoData);

        createYieldCurveChart(latestYields, oneMonthAgoYields, threeMonthsAgoYields, sixMonthsAgoYields, twelveMonthsAgoYields, latestData);
    } catch (error) {
        console.error('Error fetching data:', error);
    }
});


function processYieldData(data) {
    const maturityMap = {
        "1M": 1,
        "3M": 3,
        "6M": 6,
        "1Y": 12,
        "2Y": 24,
        "5Y": 60,
        "10Y": 120,
        "30Y": 360,
    };

    return data.map(item => {
        const maturity = maturityMap[item.maturity];
        const df = JSON.parse(item.df);
        const yieldValue = df.close_converted[Object.keys(df.close_converted)[0]];
        return [maturity, yieldValue];
    }).sort((a, b) => a[0] - b[0]);
}


function createYieldCurveChart(latestYields, oneMonthAgoYields, threeMonthsAgoYields, sixMonthsAgoYields, twelveMonthsAgoYields, yieldData) {
    Highcharts.chart('yield_curve_chart', {
        chart: {
            type: 'spline',
            backgroundColor: 'transparent',
            events: {
                load: function () {
                    this.renderer.image('/static/images/swan-icon-snow.png',
                        this.chartWidth / 2 - 125, // Center the image horizontally
                        this.chartHeight / 2 - 195, // Center the image vertically
                        250, 240 // Maintain original aspect ratio
                    ).css({
                        opacity: 0.1 // Increase opacity for visibility in dark mode
                    }).add();
                }
            }
        },
        title: {
            text: 'Yield Curve'
        },
        credits: {
            enabled: false
        },
        xAxis: {
            title: {
                text: 'Maturity (months)'
            },
            categories: yieldData.map(item => item.maturity), // Use the original maturity format for xAxis categories
            labels: {
                formatter: function () {
                    return this.value;
                },
                rotation: 270, // Rotate labels 90 degrees
                step: 2, // Show fewer labels by skipping some of them (adjust the step value as needed)
            },
            tickInterval: 12 // Adjust this value to control the number of ticks shown on the x-axis

        },
        yAxis: {
            title: {
                text: 'Yield'
            },
        },
        series: [{
            name: 'Current Yield Curve',
            data: latestYields,
            lineWidth: 5,
            dataLabels: {
                enabled: true,
                backgroundColor: 'white',
                borderColor: 'black',
                borderRadius: 3,
                borderWidth: 1,
                style: {
                    color: 'black',
                    fontSize: '12px',
                    fontWeight: 'normal',
                    textAlign: 'center',
                    textOutline: 'none',
                },
                formatter: function () {
                    const originalMaturity = yieldData.find(item => {
                        const df = JSON.parse(item.df);
                        const yieldValue = df.close_converted[Object.keys(df.close_converted)[0]];
                        return yieldValue === this.y;
                    }).maturity;
                    return `<div style="text-align: center;color:black;">${originalMaturity} Treasury<br><span class="text-large">${this.y.toFixed(2)}%</span></div>`;
                },
                useHTML: true,
                shape: 'callout',
                y: -12,
                crop: false,
                overflow: 'none',
                connectorWidth: 2,
                connectorColor: 'black',
                allowOverlap: false,
                layoutAlgorithm: 'simple-simon'
            },
            marker: {
                enabled: true,
                radius: 6,
                symbol: 'circle'
            },
        },
        {
            name: 'One Month Ago Yield Curve',
            data: oneMonthAgoYields,
            lineWidth: 1,
            dashStyle: 'ShortDot',
            color: 'white',
            dataLabels: {
                enabled: false,
            },
            marker: {
                enabled: true,
                radius: 4,
                symbol: 'circle'
            },
        },
        {
            name: 'Three Months Ago Yield Curve',
            data: threeMonthsAgoYields,
            lineWidth: 1,
            dashStyle: 'ShortDot',
            color: 'grey', // Set the line color for the three-months-ago series
            dataLabels: {
                enabled: false,
            },
            marker: {
                enabled: true,
                radius: 4,
                symbol: 'circle'
            },
        },
        {
            name: 'Six Months Ago Yield Curve',
            data: sixMonthsAgoYields,
            lineWidth: 1,
            dashStyle: 'ShortDot',
            color: 'lightgrey', // Set the line color for the six-months-ago series
            dataLabels: {
                enabled: false,
            },
            marker: {
                enabled: true,
                radius: 4,
                symbol: 'circle'
            },
        },
        {
            name: '1 Year Ago Yield Curve',
            data: twelveMonthsAgoYields,
            lineWidth: 1,
            dashStyle: 'ShortDot',
            color: 'lightblue', // Set the line color for the six-months-ago series
            dataLabels: {
                enabled: false,
            },
            marker: {
                enabled: true,
                radius: 4,
                symbol: 'circle'
            },
        }
        ]
    });
}
