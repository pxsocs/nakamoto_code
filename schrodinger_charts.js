function drawPVChart(data) {
    const finalYear = data.categories[data.categories.length - 1];
    const finalTotalValue = data.series.reduce((total, series) => total + series.data[series.data.length - 1], 0);

    Highcharts.chart('pv-container', {
        chart: {
            type: 'area',
            backgroundColor: 'transparent',
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
            }
        },
        title: {
            text: 'Future Monetization Path',
            style: {
                color: '#FFFFFF'
            }
        },
        subtitle: {
            text: 'according to assumptions',
            style: {
                color: '#C0C0C0'
            }
        },
        credits: {
            enabled: false
        },
        xAxis: {
            categories: data.categories,
            tickmarkPlacement: 'on',
            title: {
                text: '' // Remove x axis title
            },
            labels: {
                formatter: function () {
                    return this.value; // Format x-axis labels as "Year [value]"
                },
                style: {
                    color: '#C0C0C0'
                }
            }
        },
        yAxis: {
            title: {
                text: ''
            },
            labels: {
                formatter: function () {
                    return formatNumber(this.value, 0, '$'); // Format with commas and no decimal places
                },
                style: {
                    color: '#C0C0C0'
                }
            },
            plotLines: [
                {
                    color: '#fd7e14',
                    width: 2,
                    value: window.btcPrice, // Horizontal line at 'window.btcPrice'
                    zIndex: 5,
                    label: {
                        text: '&nbsp;&nbsp;Current BTC price: <span style="color:#fd7e14;">$' + formatNumber(window.btcPrice, 0) + "</span>",
                        zIndex: 6,
                        style: {
                            color: 'white',
                            fontSize: '18px',
                        }
                    }
                },
                {
                    color: '#fd7e14',
                    width: 2,
                    value: finalTotalValue, // Horizontal line at final total value
                    zIndex: 5,
                    label: {
                        text: 'Final Monetization value in year ' + finalYear + ': <span style="color:#fd7e14;">$' + formatNumber(finalTotalValue, 0) + "</span>",
                        zIndex: 6,
                        style: {
                            color: 'white',
                            fontSize: '18px'
                        }
                    }
                }
            ]
        },
        tooltip: {
            split: true,
            valueSuffix: ' BTC',
            valueDecimals: 0,
            pointFormat: '<span style="color:{point.color}">\u25CF</span> {series.name}: <b>{point.y}</b><br/>',
            footerFormat: 'Total: <b>{point.total}</b><br/>',
            formatter: function () {
                var tooltip = this.points.reduce(function (tooltip, point) {
                    return tooltip + '<span style="color:' + point.color + '">\u25CF</span> ' + point.series.name + ': <b>$' + formatNumber(point.y, 0,) + '</b><br/>';
                }, '');
                tooltip += 'Total: <b>$' + formatNumber(this.points[0].total, 0) + '</b><br/>';

                return tooltip;
            },
            backgroundColor: 'rgba(72, 72, 72, 0.8)',
            borderColor: '#C0C0C0',
            style: {
                color: '#FFFFFF'
            }
        },
        plotOptions: {
            area: {
                stacking: 'normal',
                lineColor: 'white',
                lineWidth: 1,
                animation: false,
                marker: {
                    enabled: false // Disable markers
                },
                dataLabels: {
                    enabled: false,
                }
            }
        },
        legend: {
            enabled: false // Remove legend
        },
        colors: ['#FFFFFF', '#D9D9D9', '#B3B3B3', '#8C8C8C', '#666666', '#404040'],

        series: data.series
    });
};
