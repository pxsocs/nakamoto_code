//  HELPER FUNCTION

// Slider Formatting and funcionality

$(document).ready(function () {

});


(function ($) {
    $.fn.animateNumbers = function (stop, commas, duration, ease) {
        return this.each(function () {
            var $this = $(this);
            var start = parseInt($this.text().replace(/,/g, ""));
            commas = (commas === undefined) ? true : commas;
            $({ value: start }).animate({ value: stop }, {
                duration: duration == undefined ? 1000 : duration,
                easing: ease == undefined ? "swing" : ease,
                step: function () {
                    $this.text(Math.floor(this.value));
                    if (commas) { $this.text($this.text().replace(/(\d)(?=(\d\d\d)+(?!\d))/g, "$1,")); }
                },
                complete: function () {
                    if (parseInt($this.text()) !== stop) {
                        $this.text(stop);
                        if (commas) { $this.text($this.text().replace(/(\d)(?=(\d\d\d)+(?!\d))/g, "$1,")); }
                    }
                }
            });
        });
    };
})(jQuery);

// Formatter for numbers use
// prepend for currencies, for positive / negative, include prepend = +
// Small_pos signals to hide result - this is due to small positions creating
// unrealistic breakevens (i.e. too small or too large)
function formatNumber(amount, decimalCount = 2, prepend = '', postpend = '', small_pos = 'False', up_down = false, red_green = false) {
    if (((amount == 0) | (amount == null)) | (small_pos == 'True')) {
        return '-'
    }
    try {
        var string = ''
        string += (amount).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: decimalCount, minimumFractionDigits: decimalCount })
        if ((prepend == '+') && (amount > 0)) {
            string = "+" + string
        } else if ((prepend == '+') && (amount <= 0)) {
            string = string
        } else {
            string = prepend + string
        }

        if (up_down == true) {
            if (amount > 0) {
                postpend = postpend + '&nbsp;<img src="static/images/btc_up.png" width="10" height="10"></img>'
            } else if (amount < 0) {
                postpend = postpend + '&nbsp;<img src="static/images/btc_down.png" width="10" height="10"></img>'
            }
        }
        if (red_green == true) {
            if (amount > 0) {
                string = "<span style='color: green'>" + string + "<span>"
            } else if (amount < 0) {
                string = "<span style='color: red'>" + string + "<span>"
            }
        }

        return (string + postpend)
    } catch (e) {
        console.log(e)
    }
};


function formatDate(date) {
    var year = date.getFullYear();

    var month = (1 + date.getMonth()).toString();
    month = month.length > 1 ? month : '0' + month;

    var day = date.getDate().toString();
    day = day.length > 1 ? day : '0' + day;

    return month + '/' + day + '/' + year;
}

function formatDateTime(date) {
    var hours = date.getHours();
    var minutes = date.getMinutes();
    var ampm = hours >= 12 ? 'pm' : 'am';
    hours = hours % 12;
    hours = hours ? hours : 12; // the hour '0' should be '12'
    minutes = minutes < 10 ? '0' + minutes : minutes;
    var strTime = hours + ':' + minutes + ' ' + ampm;
    return (date.getMonth() + 1) + "/" + date.getDate() + "/" + date.getFullYear() + "  " + strTime;
}

function formatDateString(dateString) {
    const date = new Date(dateString);
    const formattedDate = `${date.getMonth() + 1}/${date.getDate()}/${date.getFullYear().toString().substr(-2)}`;
    return formattedDate;
}

var getUrlParameter = function getUrlParameter(sParam) {
    var sPageURL = window.location.search.substring(1),
        sURLVariables = sPageURL.split('&'),
        sParameterName,
        i;

    for (i = 0; i < sURLVariables.length; i++) {
        sParameterName = sURLVariables[i].split('=');

        if (sParameterName[0] === sParam) {
            return sParameterName[1] === undefined ? true : decodeURIComponent(sParameterName[1]);
        }
    }
};




function heat_color(object, inverse = false) {
    // Get all data values from our table cells making sure to ignore the first column of text
    // Use the parseInt function to convert the text string to a number


    // Let's create a heatmap on all heatmap values
    // Function to get the max value in an Array
    Array.max = function (array) {
        return Math.max.apply(Math, array);
    };

    // Function to get the min value in an Array
    Array.min = function (array) {
        return Math.min.apply(Math, array);
    };

    var counts_positive = $(object).map(function () {
        if (parseInt($(this).text()) > 0) {
            return parseInt($(this).text());
        };
    }).get();

    var counts_negative = $(object).map(function () {
        if (parseInt($(this).text()) < 0) {
            return parseInt($(this).text());
        };
    }).get();

    // run max value function and store in variable
    var max = Array.max(counts_positive);
    var min = Array.min(counts_negative) * (-1);

    n = 100; // Declare the number of groups

    // Define the ending colour, which is white
    xr = 250; // Red value
    xg = 250; // Green value
    xb = 250; // Blue value

    // Define the starting colour for positives
    yr = 165; // Red value 243
    yg = 255; // Green value 32
    yb = 165; // Blue value 117

    if (inverse == true) {
        // Define the starting colour for negatives
        yr = 80; // Red value 243
        yg = 130; // Green value 32
        yb = 200 // Blue value 117
    }

    // Define the starting colour for negatives
    nr = 255; // Red value 243
    ng = 120; // Green value 32
    nb = 120; // Blue value 117

    // Loop through each data point and calculate its % value
    $(object).each(function () {
        if (parseInt($(this).text()) > 0) {
            var val = parseInt($(this).text());
            var pos = parseInt((Math.round((val / max) * 100)).toFixed(0));
            red = parseInt((xr + ((pos * (yr - xr)) / (n - 1))).toFixed(0));
            green = parseInt((xg + ((pos * (yg - xg)) / (n - 1))).toFixed(0));
            blue = parseInt((xb + ((pos * (yb - xb)) / (n - 1))).toFixed(0));
            clr = 'rgb(' + red + ',' + green + ',' + blue + ')';
            $(this).closest('td').css({ backgroundColor: clr });
        }
        else {
            var val = parseInt($(this).text()) * (-1);
            var pos = parseInt((Math.round((val / max) * 100)).toFixed(0));
            red = parseInt((xr + ((pos * (nr - xr)) / (n - 1))).toFixed(0));
            green = parseInt((xg + ((pos * (ng - xg)) / (n - 1))).toFixed(0));
            blue = parseInt((xb + ((pos * (nb - xb)) / (n - 1))).toFixed(0));
            clr = 'rgb(' + red + ',' + green + ',' + blue + ')';
            $(this).closest('td').css({ backgroundColor: clr });
        }
    });
}


function sleep(milliseconds) {
    var start = new Date().getTime();
    for (var i = 0; i < 1e7; i++) {
        if ((new Date().getTime() - start) > milliseconds) {
            break;
        }
    }
}


function export_table(table_id) {
    var titles = [];
    var data = [];

    /*
     * Get the table headers, this will be CSV headers
     * The count of headers will be CSV string separator
     */
    $('#' + table_id + ' th').each(function () {
        var cellData = $(this).text();
        var cleanData = escape(cellData);
        var cleanData = cellData.replace(/,/g, "");
        var cleanData = cleanData.replace(/\s+/g, "  ");
        titles.push(cleanData);
    });

    /*
     * Get the actual data, this will contain all the data, in 1 array
     */
    $('#' + table_id + ' td').each(function () {
        var cellData = $(this).text();
        var cleanData = escape(cellData);
        var cleanData = cellData.replace(/,/g, "");
        var cleanData = cleanData.replace(/\s+/g, "  ");
        data.push(cleanData);
    });


    /*
     * Convert our data to CSV string
     */
    var CSVString = prepCSVRow(titles, titles.length, '');
    CSVString = prepCSVRow(data, titles.length, CSVString);

    /*
     * Make CSV downloadable
     */
    var downloadLink = document.createElement("a");
    var blob = new Blob(["\ufeff", CSVString]);
    var url = URL.createObjectURL(blob);
    downloadLink.href = url;
    downloadLink.download = "download_" + table_id + "_data.csv";

    /*
     * Actually download CSV
     */
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
};

/*
* Convert data array to CSV string
* @param arr {Array} - the actual data
* @param columnCount {Number} - the amount to split the data into columns
* @param initial {String} - initial string to append to CSV string
* return {String} - ready CSV string
*/
function prepCSVRow(arr, columnCount, initial) {
    var row = ''; // this will hold data
    var delimeter = ';'; // data slice separator, in excel it's `;`, in usual CSv it's `,`
    var newLine = '\n'; // newline separator for CSV row

    /*
     * Convert [1,2,3,4] into [[1,2], [3,4]] while count is 2
     * @param _arr {Array} - the actual array to split
     * @param _count {Number} - the amount to split
     * return {Array} - splitted array
     */
    function splitArray(_arr, _count) {
        var splitted = [];
        var result = [];
        _arr.forEach(function (item, idx) {
            if ((idx + 1) % _count === 0) {
                splitted.push(item);
                result.push(splitted);
                splitted = [];
            } else {
                splitted.push(item);
            }
        });
        return result;
    }
    var plainArr = splitArray(arr, columnCount);
    // don't know how to explain this
    // you just have to like follow the code
    // and you understand, it's pretty simple
    // it converts `['a', 'b', 'c']` to `a,b,c` string
    plainArr.forEach(function (arrItem) {
        arrItem.forEach(function (item, idx) {
            row += item + ((idx + 1) === arrItem.length ? '' : delimeter);
        });
        row += newLine;
    });
    return initial + row;
}

// -----------------------------------------------------------------
// HighCharts --- Create Simple charts templates
// -----------------------------------------------------------------

// PIE CHART
// receives: pie_chart (data) in format:
//          [{
//          'name': string,
//          'y': float,
//          'color': hex color
//          }, {....}]
// series_name
// target_div
function draw_pie_chart(pie_chart, series_name, target_div) {
    Highcharts.chart(target_div, {
        chart: {
            type: 'pie'
        },
        credits: {
            text: " ",
            style: {
                fontSize: '10px',
                color: '#363636'
            },
            position: {
                align: 'right',
                y: -5
            },
            href: " "
        },
        title: {
            text: null
        },
        tooltip: {
            pointFormat: '{series.name}: <b>{point.percentage:.1f}%</b>'
        },
        accessibility: {
            point: {
                valueSuffix: '%'
            }
        },
        plotOptions: {
            pie: {
                allowPointSelect: true,
                cursor: 'pointer',
                dataLabels: {
                    enabled: true,
                    format: '<b>{point.name}</b>: {point.percentage:.1f} %',
                    style: {
                        fontSize: '10px',
                        color: '#363636'
                    },
                },
            }
        },
        series: [{
            name: series_name,
            data: pie_chart
        }]
    });
}


// Draws a basic chart with limited customization
// chart_types: line, bar, etc... These are the highchart chart types
// chart_data in format :
//              [{
//              name: name,
//              data: data
//              }]
function draw_simple_chart(chart_type, bins, chart_data, name, title, subtitle, target_div) {
    Highcharts.chart(target_div, {
        chart: {
            type: chart_type
        },
        title: {
            text: title
        },
        subtitle: {
            text: subtitle
        },
        xAxis: {
            categories: bins,
            title: {
                text: null
            }
        },
        yAxis: {
            min: 0,
            title: {
                text: name,
                align: 'high'
            },
            labels: {
                overflow: 'justify'
            }
        },
        tooltip: {
            valueSuffix: ''
        },
        plotOptions: {
            bar: {
                dataLabels: {
                    enabled: true
                }
            }
        },
        legend: {
            enabled: false,
        },
        credits: {
            enabled: false
        },
        series: chart_data
    });
}


// Returns a csv from an array of objects with
// values separated by commas and rows separated by newlines
function CSV(array) {

    var result = ''
    for (var key in array) {
        if (array.hasOwnProperty(key)) {
            result += key + "," + array[key] + "\n";
        }
    }
    return result;

}

// Save txt into filename
function download(filename, text) {
    var pom = document.createElement('a');
    pom.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
    pom.setAttribute('download', filename);

    if (document.createEvent) {
        var event = document.createEvent('MouseEvents');
        event.initEvent('click', true, true);
        pom.dispatchEvent(event);
    }
    else {
        pom.click();
    }
}

function updateURLParameter(url, param, paramVal) {
    var TheAnchor = null;
    var newAdditionalURL = "";
    var tempArray = url.split("?");
    var baseURL = tempArray[0];
    var additionalURL = tempArray[1];
    var temp = "";

    if (additionalURL) {
        var tmpAnchor = additionalURL.split("#");
        var TheParams = tmpAnchor[0];
        TheAnchor = tmpAnchor[1];
        if (TheAnchor)
            additionalURL = TheParams;

        tempArray = additionalURL.split("&");

        for (var i = 0; i < tempArray.length; i++) {
            if (tempArray[i].split('=')[0] != param) {
                newAdditionalURL += temp + tempArray[i];
                temp = "&";
            }
        }
    }
    else {
        var tmpAnchor = baseURL.split("#");
        var TheParams = tmpAnchor[0];
        TheAnchor = tmpAnchor[1];

        if (TheParams)
            baseURL = TheParams;
    }

    if (TheAnchor)
        paramVal += "#" + TheAnchor;

    var rows_txt = temp + "" + param + "=" + paramVal;
    return baseURL + "?" + newAdditionalURL + rows_txt;
}


function copyTable(el) {
    var body = document.body, range, sel;
    if (document.createRange && window.getSelection) {
        range = document.createRange();
        sel = window.getSelection();
        sel.removeAllRanges();
        try {
            range.selectNodeContents(el);
            sel.addRange(range);
        } catch (e) {
            range.selectNode(el);
            sel.addRange(range);
        }
    } else if (body.createTextRange) {
        range = body.createTextRange();
        range.moveToElementText(el);
        range.select();
    }
    document.execCommand("Copy");
}


function pkl_grabber(pickle_file, interval_ms, target_element, status_element = undefined) {
    const socket = new WebSocket("ws://" + location.host + "/pickle");
    socket.addEventListener("message", (ev) => {
        $(target_element).html(ev.data);
    });

    // Executes the function every 1000 milliseconds
    const interval = setInterval(function () {
        if (socket.readyState === WebSocket.CLOSED) {
            if (status_element != undefined) {
                $(status_element).html("<span style='color: red'>Disconnected</span>");
            }
            $(target_element).text("WebSocket Error -- Check if app is running");
        } else {
            socket.send(pickle_file);
            if (status_element != undefined) {
                $(status_element).html("<span style='color: darkgreen'>Connected</span>");
            }
        }
    }, interval_ms);
}



function timeDifference(current, previous, just_now_precision_seconds = 50) {

    var msPerMinute = 60 * 1000;
    var msPerHour = msPerMinute * 60;
    var msPerDay = msPerHour * 24;
    var msPerMonth = msPerDay * 30;
    var msPerYear = msPerDay * 365;

    var elapsed = current - previous;


    if (isNaN(parseFloat(elapsed))) {
        return ("Never")
    }

    if (elapsed < msPerMinute) {
        if (elapsed <= (just_now_precision_seconds * 1000)) {
            return "just now"
        } else {
            return Math.round(elapsed / 1000) + ' seconds ago';
        }
    }

    else if (elapsed < msPerHour) {
        return Math.round(elapsed / msPerMinute) + ' minutes ago';
    }

    else if (elapsed < msPerDay) {
        return Math.round(elapsed / msPerHour) + ' hours ago';
    }

    else if (elapsed < msPerMonth) {
        return 'approximately ' + Math.round(elapsed / msPerDay) + ' days ago';
    }

    else if (elapsed < msPerYear) {
        return 'approximately ' + Math.round(elapsed / msPerMonth) + ' months ago';
    }

    else {
        return 'approximately ' + Math.round(elapsed / msPerYear) + ' years ago';
    }
}


function send_message(message, bg = 'info', message_element = '#alertsection') {
    if (message == 'clear') {
        $(message_element).html("");
        $(message_element).hide("medium");
        return
    }
    var uniqid = Date.now();
    new_html = `
    <div class="col">
        <div id='${uniqid}' class="alert alert-${bg} alert-dismissible" role="alert" data-alert="alert">
            <strong>${message}</strong>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    </div>
    `;
    $(message_element).html(new_html);
    $(message_element).show("medium");
}


function base_url() {
    return location.protocol + "//" + location.host + "/";
}


function ajax_getter(url, dataType = 'json') {
    // Note that this is NOT an asynchronous request.
    return_data = "Empty Data";
    $.ajax({
        type: "GET",
        dataType: 'json',
        url: url,
        async: false,
        success: function (data) {
            return_data = data
        },
        error: function (xhr, status, error) {
            return_data = ("Error on request. status: " + status + " error:" + error);
        }
    });
    return return_data;
}

// Sort a list of objects by a certain key
function sortObj(list, key, reverse = false) {
    try {
        function compare(a, b) {
            a = a[key];
            b = b[key];
            var type = (typeof (a) === 'string' ||
                typeof (b) === 'string') ? 'string' : 'number';
            var result;
            if (type === 'string') result = a.localeCompare(b);
            else result = a - b;
            return result;
        }
        if (reverse == true) {
            return list.sort(compare).reverse();
        } else {
            return list.sort(compare);
        }

    } catch (e) {
        console.log("Error sorting list: " + e);
        return list;

    }
}

// source: https://stackoverflow.com/questions/64254355/cut-string-into-chunks-without-breaking-words-based-on-max-length
function splitString(n, str) {
    let arr = str?.split(' ');
    let result = []
    let subStr = arr[0]
    for (let i = 1; i < arr.length; i++) {
        let word = arr[i]
        if (subStr.length + word.length + 1 <= n) {
            subStr = subStr + ' ' + word
        }
        else {
            result.push(subStr);
            subStr = word
        }
    }
    if (subStr.length) { result.push(subStr) }
    return result
}


function initialize_tooltips() {
    $(".tooltip").tooltip("hide");
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    })

}

// Shorten strings
String.prototype.trimEllip = function (length) {
    beg_end = (length / 2);
    tail_str = this.substr(this.length - beg_end);
    return this.length > length ? this.substring(0, beg_end) + "..." + tail_str : this;
}


function sats_btc(sats) {
    sats = parseInt(sats);
    if (sats <= 100000000) {
        return formatNumber(sats, 0, '', ' sats')
    } else {
        sats = parseFloat(sats) / 100000000;
        return formatNumber(sats, 8, '₿ ')
    }
}


// ARRAY Functions

function normalizeArrayBase100(array) {
    if (array.length === 0) {
        console.error("The input array must not be empty.");
        return;
    }

    let firstElement = array[0];
    let normalizedArray = array.map(element => (element / firstElement) * 100);

    return normalizedArray;
}

function weightedSumArray(arrayA, arrayB, weightA, weightB) {
    if (arrayA.length !== arrayB.length) {
        console.error("The input arrays must have the same length.");
        return;
    }

    let resultArray = [];
    for (let i = 0; i < arrayA.length; i++) {
        resultArray.push(arrayA[i] * weightA + arrayB[i] * weightB);
    }

    return resultArray;
}


function createArray(initial_value, final_value, linear_years, perp_rate, total_years) {
    let result = [];
    let linear_growth_rate = (final_value - initial_value) / (linear_years - 1);

    for (let i = 1; i <= total_years; i++) {
        if (i <= linear_years) {
            result.push(initial_value + (i - 1) * linear_growth_rate);
        } else {
            result.push(result[i - 2] * (1 + perp_rate));
        }
    }

    return result;
}



function adjustFontSize() {
    var screenWidth = $(window).width();
    if (screenWidth <= 768) {
        $('body').css('font-size', '50%');
    } else {
        $('body').css('font-size', '100%');
    }
}


function isMobileDevice() {
    const userAgent = navigator.userAgent;
    return /Android|webOS|iPhone|BlackBerry|IEMobile|Opera Mini/i.test(userAgent) &&
        !/iPad|Tablet/i.test(userAgent);
}

function updateOrientation() {
    const rotateDevice = document.getElementById('rotate-device');
    if (isMobileDevice()) {
        if (window.innerWidth < window.innerHeight) {
            // Device is in portrait mode, show the message
            rotateDevice.style.display = 'flex';
        } else {
            // Device is in landscape mode, hide the message
            rotateDevice.style.display = 'none';
        }
    } else {
        // Not a mobile device, hide the message
        rotateDevice.style.display = 'none';
    }
}

function createDateRanges(start_date, end_date) {
    // Parse string dates into JavaScript Date objects
    const startDate = new Date(start_date);
    const endDate = new Date(end_date);

    // Initialize the list of date ranges
    const dateRanges = [];

    // Loop through the years from start date to end date
    for (let year = startDate.getFullYear(); year <= endDate.getFullYear(); year++) {
        // Set the beginning of the year
        const startOfYear = new Date(year, 0, 1); // January 1st
        const endOfYear = new Date(year, 11, 31); // December 31st

        // Adjust the start and end of the range based on the start and end dates
        const rangeStart = year === startDate.getFullYear() ? startDate : startOfYear;
        const rangeEnd = year === endDate.getFullYear() ? endDate : endOfYear;

        // Format the date range as strings and add it to the list
        dateRanges.push([
            (rangeStart.getMonth() + 1) + '/' + rangeStart.getDate() + '/' + rangeStart.getFullYear(),
            (rangeEnd.getMonth() + 1) + '/' + rangeEnd.getDate() + '/' + rangeEnd.getFullYear()
        ]);
    }

    return dateRanges;
}


// Function to parse the URL and get the query parameters
// usage:
// // Get the query parameters
//     var queryParams = getUrlVars();

//     // Fill the input fields with the parsed query parameters if they exist and have valid values
//     if (queryParams['age'] && !isNaN(queryParams['age'])) {
//         $("#age").val(queryParams['age']);
//     }
function getUrlVars() {
    var vars = {};
    var parts = window.location.href.replace(/[?&]+([^=&]+)=([^&]*)/gi, function (m, key, value) {
        vars[key] = value;
    });
    return vars;
}


function sortTable(tbody, sortColumn = '.sortfield', ascending = false) {
    let rows = tbody.find('tr:not(.totals-row)').toArray();

    rows.sort(function (a, b) {
        let aValue = parseFloat($(a).find(sortColumn).text().replace(/,/g, ''));
        let bValue = parseFloat($(b).find(sortColumn).text().replace(/,/g, ''));
        return ascending ? aValue - bValue : bValue - aValue;
    });

    let animationDuration = 800; // Duration of the animation in milliseconds

    rows.forEach((row, index) => {
        let currentRow = $(row);
        let currentRowPosition = currentRow.position();
        let newRowPosition = tbody.children().eq(index).position();

        if (currentRowPosition.top !== newRowPosition.top) {
            currentRow.css({
                position: 'relative',
                top: currentRowPosition.top - newRowPosition.top,
                opacity: 0
            }).animate({
                top: 0,
                opacity: 1
            }, animationDuration, function () {
                currentRow.css({
                    position: '',
                    top: '',
                    opacity: ''
                });
            });
        }
    });

    tbody.append(rows);
}


function titleCase(str) {
    var splitStr = str.toLowerCase().split(' ');
    for (var i = 0; i < splitStr.length; i++) {
        // You do not need to check if i is larger than splitStr length, as your for does that for you
        // Assign it back to the array
        splitStr[i] = splitStr[i].charAt(0).toUpperCase() + splitStr[i].substring(1);
    }
    // Directly return the joined string
    return splitStr.join(' ');
}