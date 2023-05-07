$(document).ready(function () {

    // Enable Tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]')
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl))

    // Tutorial and listeners
    // Define the tutorial data structure
    var tutorialData = {
        1: { "title": "Inputs", "focus-on": "bitcoin_fv", "info": "<h5>This is the discount rate</h5> Here, you can do xyz", "default_value": 3 },
        2: { "title": "Inputs2", "focus-on": "page-content-wrapper", "info": "<h5>Tddddhis is the discount rate</h5> Here, you can do xyz", "default_value": 4 },
    };

    // Start tutorial on button click
    $("#start-tutorial").click(function () {
        startTutorial(tutorialData);
    });


    $('.toggleTable').click(function () {
        let icon = $(this).find('.rotate-icon');
        let table = $(this).closest('.datagroup').find('.table'); // Find the table element in the corresponding col-6 div

        // Toggle table visibility and animate the arrow icon
        if (table.is(":visible")) {
            table.closest('.table-responsive').slideUp(900, function () {
                icon.toggleClass('fa-chevron-down fa-chevron-up rotate');
            });
        } else {
            table.closest('.table-responsive').slideDown(900, function () {
                icon.toggleClass('fa-chevron-down fa-chevron-up rotate');
            });
        }
    });


    $('.toggleCard').click(function () {
        console.log("toggleCard");
        let icon = $(this).find('.rotate-icon');
        let card = $(this).parent().parent().find('.showhidecard');

        // Toggle card visibility and animate the arrow icon
        card.slideToggle(900, function () {
            icon.toggleClass('fa-chevron-down fa-chevron-up rotate');
        });
    });

    $('.cds-btn').click(function () {
        $('html, body').animate({
            scrollTop: $('#cds-assumptions').offset().top
        }, 900);
    });

    $('.debt-btn').click(function () {
        $('html, body').animate({
            scrollTop: $('#debt-assumptions').offset().top
        }, 900);
    });

    $('.met-btn').click(function () {
        $('html, body').animate({
            scrollTop: $('#met-assumptions').offset().top
        }, 900);
    });


    // Startup Functions
    window.BTC_price = 30000;
    getBTCPrice();
    updateAllTotals();
    update20YrCDSandPD();
    updateBitcoinFairValue();
    generate_prob_def_chart();
    generate_debt_chart();

    buildTable();

    // Updates BTC Price every 2 minutes
    window.setInterval(function () {
        getBTCPrice();
    }, 120000);


    // Listener
    $("#horizon-premium").on("change", update20YrCDSandPD);

    let chartUpdateTimeout = null;

    $("#horizon-premium-slider").on("input", function () {
        const sliderValue = $(this).val();
        $("#horizon-premium-display").text(sliderValue + "%");
        $("#horizon-premium").val(sliderValue);
        update20YrCDSandPD();
        updateBitcoinFairValue();
        buildTable();

        // Clear the existing timeout if it exists
        if (chartUpdateTimeout) {
            clearTimeout(chartUpdateTimeout);
        }

        // Set a new timeout to update the chart after 2 seconds
        chartUpdateTimeout = setTimeout(() => {
            // Update the chart here
            // For example, if you have a function called updateChart() to update the map:

        }, 2000);
    });


    // Event delegation for handling editable cells
    $('#cdsTable tbody').on('click', '.editable', function () {
        let cell = $(this);
        if (!cell.find('input').length) {
            let input = $('<input class="text-right">', {
                type: 'number',
                value: cell.attr('data-value')
            }).css('width', '70px');

            input.on('blur', function () {
                let newValue = parseInt(input.val().replace(/,/g, ''));
                if (isNaN(newValue)) newValue = 0;
                cell.text(newValue.toLocaleString());
                cell.attr('data-value', newValue);
                input.remove();
                update20YrCDSandPD();
                buildTable();
            });

            cell.parent().find("td:eq(0) input[type='checkbox']").prop("checked", true);
            cell.text('').append(input);
            input.focus();
        }
    });

    // Checkbox listener
    $("#cdsTable tbody").on("click", "input[type='checkbox']", function () {
        updateBitcoinFairValue();
        update20YrCDSandPD();
        updateAllTotals();
        buildTable();


    });


    // Event delegation for handling editable cells
    $('#debtTable tbody').on('click', '.editable', function () {
        let cell = $(this);
        if (!cell.find('input').length) {
            let input = $('<input class="text-right">', {
                type: 'text',
                value: cell.attr('data-value')
            }).css('width', '100px');

            input.on('blur', function () {
                let newValue = parseInt(input.val().replace(/,/g, ''));
                if (isNaN(newValue)) newValue = 0;
                cell.text(newValue.toLocaleString());
                cell.attr('data-value', newValue);
                input.remove();
                updateAllTotals();
                buildTable();
            });


            cell.text('').append(input);
            input.focus();
        }
    });

});


function getBTCPrice() {
    // Get BTC Price
    fetch("/realtime_btc")
        .then((response) => response.json())
        .then((data) => {
            $("#bitcoin_price").html(formatNumber(data.btc_usd, 0, '$ '));
            window.BTC_price = data.btc_usd;
            updateAllTotals();
            update20YrCDSandPD();
            updateBitcoinFairValue();
            buildTable();
        });

}


function updateAllTotals() {
    let totalDomestic = 0;
    let totalInternational = 0;
    let totalUnfunded = 0;

    $('#debtTable tbody tr').each(function () {
        let domestic = parseInt($(this).find('td:eq(0)').attr('data-value').replace(/,/g, ''));
        let international = parseInt($(this).find('td:eq(2)').attr('data-value').replace(/,/g, ''));
        let unfunded = parseInt($(this).find('td:eq(4)').attr('data-value').replace(/,/g, ''));

        totalDomestic += domestic;
        totalInternational += international;
        totalUnfunded += unfunded;

        let total = domestic + international + unfunded;
        $(this).find('td:eq(5)').text(total.toLocaleString()).addClass('total');

    });

    $('#totalDomestic').text(totalDomestic.toLocaleString());
    $('#totalInternational').text(totalInternational.toLocaleString());
    $('#totalUnfunded').text(totalUnfunded.toLocaleString());
    $('#grandTotal').text((totalDomestic + totalInternational + totalUnfunded).toLocaleString());
    sortTable($('#debtTable tbody'));
    updateBitcoinFairValue();
};



function update20YrCDSandPD() {
    const horizonPremium = parseFloat($("#horizon-premium").val().replace("%", "")) / 100;

    $("#cdsTable tbody tr").each(function () {
        const row = $(this);
        const fiveYrCDS = parseFloat(row.find("td:eq(2)").text().replace(/,/g, ""));
        const probabilityOfDefault5 = 1 - Math.exp(-fiveYrCDS / 10000 * 5);
        const twentyYrCDS = fiveYrCDS * (1 + horizonPremium);
        const probabilityOfDefault = 1 - Math.exp(-twentyYrCDS / 10000 * 20);

        row.find("td:eq(3)").html(
            probabilityOfDefault > 0.85
                ? '<span class="float-center text-warning"><i class="fas fa-skull"></i></span>'
                : formatNumber(probabilityOfDefault5 * 100, 2) + '%'
        );

        row.find("td:eq(6)").text(formatNumber(twentyYrCDS, 2));
        row.find("td:eq(7)").html(
            probabilityOfDefault > 0.85
                ? '<span class="float-center text-warning"><i class="fas fa-skull"></i></span>'
                : formatNumber(probabilityOfDefault * 100, 2) + '%'
        );
        // Uncheck the row checkbox if probabilityOfDefault > 0.85
        if (probabilityOfDefault > 0.85) {
            row.find("td:eq(0) input[type='checkbox']").prop("checked", false);
        }
    });
    sortTable($('#cdsTable tbody'), 'td:nth-child(4)', ascending = true);
    updateBitcoinFairValue();
}



function updateBitcoinFairValue() {
    const totalBitcoins = 20999999.9769;

    let totalDebt = 0;
    let weightedAvgProbabilityOfDefault = 0;
    let bitcoinFairValue = 0;

    $("#cdsTable tbody tr").each(function () {
        const row = $(this);
        const isChecked = row.find("td:eq(0) input[type='checkbox']").is(":checked");

        if (isChecked) {
            const countryCode = row.find("th:eq(0)").text().trim();
            const probabilityOfDefault = parseFloat(row.find("td:eq(7)").text().replace(/,/g, "").replace("%", "")) / 100;
            const twentyYrCDS = parseFloat(row.find("td:eq(6)").text().replace(/,/g, ""));




            // Get the total debt for the corresponding country in the debtTable
            $("#debtTable tbody tr").each(function () {
                const debtRow = $(this);
                if (debtRow.find("th:eq(0)").text().trim() === countryCode) {
                    const debtValue = parseInt(debtRow.find("td:eq(5)").text().replace(/,/g, ""));
                    totalDebt += debtValue;
                    weightedAvgProbabilityOfDefault += probabilityOfDefault * debtValue;

                }
            });
        }
    });

    if (totalDebt > 0) {
        weightedAvgProbabilityOfDefault /= totalDebt;
        bitcoinFairValue = totalDebt * weightedAvgProbabilityOfDefault / totalBitcoins * 100000;
    }

    $("#total_debt_sel").text(formatNumber(totalDebt, 0));
    $("#wa_pd").text(formatNumber(weightedAvgProbabilityOfDefault * 100, 0) + '%');

    btc_diff = (bitcoinFairValue / window.BTC_price) - 1;
    if (btc_diff < 1) {
        btc_diff = (btc_diff) * 100;
        $("#bitcoin_fv").html("$ " + formatNumber(bitcoinFairValue, 0) + "&nbsp;&nbsp;<span class='text-60-small text-white'>(" + formatNumber(btc_diff, 2) + "%)</span>");
    } else {
        btc_diff = btc_diff + 1;
        $("#bitcoin_fv").html("$ " + formatNumber(bitcoinFairValue, 0) + "&nbsp;&nbsp;<span class='text-60-small text-white'>(" + formatNumber(btc_diff, 2) + "x)</span>");
    }
}


function buildMapData() {
    let mapData = [];

    $("#cdsTable tbody tr").each(function () {
        const row = $(this);
        const countryName = row.find("th:eq(0)").text().trim();
        const cds = parseFloat(row.find("td:eq(2)").text().replace(/,/g, ""));
        const probabilityOfDefault = parseFloat(row.find("td:eq(7)").text().replace(/,/g, "").replace("%", ""));

        let totalDebt = 0;
        $("#debtTable tbody tr").each(function () {
            const debtRow = $(this);
            if (debtRow.find("th:eq(0)").text().trim() === countryName) {
                totalDebt = parseInt(debtRow.find("td:eq(5)").text().replace(/,/g, ""));
            }
        });

        // Retrieve the ISO 3166-1 alpha-3 country code from the countryCodeMapping object
        const countryCode = countryCodeMapping[countryName] || '';

        // Retrieve the flag URL directly from the table row
        const flagUrl = row.find("img").attr("src");

        mapData.push({
            "country": countryName,
            "cds": cds,
            "probabilityOfDefault": probabilityOfDefault,
            "totalDebt": totalDebt,
            "flagUrl": flagUrl
        });
    });
    return mapData;
}

function buildTable() {
    var countriesToHighlight = buildMapData();
    $("#country-table").html('')
    countriesToHighlight.forEach(country => {
        const countryCode = country.code;
        const countryName = country.country;
        const flagUrl = country.flagUrl; // Use the flag URL from the table data
        const cds = formatNumber(country.cds, 0);
        const probabilityOfDefault = formatNumber(country.probabilityOfDefault, 0);
        const totalDebt = formatNumber(country.totalDebt / 1000000, 2);

        const countryBox = `
      <td class="country-box">
        <img class="flag" src="${flagUrl}" alt="${countryName} flag" />
            <div class='country-text'>
                <span class="text-large">
                ${countryName}</span><br>
                CDS <strong class="float-end">${cds} bps</strong><br>
                Default prob <strong class="float-end">${probabilityOfDefault}%</strong><br>
                Debt <strong class="float-end">${totalDebt} tri</strong>
            </div>
      </td>
    `;

        // Append the country box to the table
        $("#country-table").append(countryBox);
    });
}



const countryCodeMapping = {
    'Australia': 'AUS',
    'Austria': 'AUT',
    'Belgium': 'BEL',
    'Canada': 'CAN',
    'China': 'CHN',
    'Czech Republic': 'CZE',
    'Denmark': 'DNK',
    'Egypt': 'EGY',
    'Finland': 'FIN',
    'France': 'FRA',
    'Germany': 'DEU',
    'Greece': 'GRC',
    'Hungary': 'HUN',
    'Indonesia': 'IDN',
    'Ireland': 'IRL',
    'Italy': 'ITA',
    'Japan': 'JPN',
    'South Korea': 'KOR',
    'Luxembourg': 'LUX',
    'Mexico': 'MEX',
    'Netherlands': 'NLD',
    'Norway': 'NOR',
    'Poland': 'POL',
    'Portugal': 'PRT',
    'Slovakia': 'SVK',
    'Spain': 'ESP',
    'Sweden': 'SWE',
    'Switzerland': 'CHE',
    'Turkey': 'TUR',
    'United Kingdom': 'GBR',
    'United States': 'USA',
    'Chile': 'CHL',
    'Estonia': 'EST',
    'Israel': 'ISR',
    'Slovenia': 'SVN',
    'Iceland': 'ISL',
    'Latvia': 'LVA',
    'Colombia': 'COL',
    'Lithuania': 'LTU',
    'New Zealand': 'NZL',
    'Brazil': 'BRA',
    'Romania': 'ROU',
    'Russia': 'RUS',
    'Other Advanced Economies Average': 'OAA',
    'OECD Countries': 'OEC'
};


// Function to generate the data for the horizon premium chart.
function generate_prob_def_chart() {
    const data = [];
    total_debt = parseFloat($("#total_debt_sel").text().replace("%", "")) * 1000000;
    bitcoins = 20999999.9769;
    for (let i = 0; i <= 80; i += 10) {
        const p_def = i / 100;
        const valuation = total_debt * 100000 * p_def / bitcoins
        data.push([valuation, p_def]);
    }

    // Create the horizon premium chart.
    // Create the horizon premium chart.
    Highcharts.chart('horizon-premium-chart', {
        chart: {
            type: 'spline',
            backgroundColor: 'transparent'
        },
        title: {
            text: 'Bitcoin Valuation by Probability of Default',
            style: { fontSize: '14px', color: 'white' }
        },
        xAxis: {
            title: { text: 'Bitcoin Price' },
            labels: { style: { color: 'white' } },
            gridLineColor: '#444',
            gridLineWidth: 1,
            minorGridLineColor: '#444',
            minorGridLineWidth: 1,
            minorTickInterval: 'auto'
        },
        yAxis: {
            title: { text: 'Probability of Default (%)' },
            labels: {
                formatter: function () { return this.value * 100 + '%'; },
                style: { color: 'white' }
            },
            gridLineColor: '#444',
            gridLineWidth: 1,
            startOnTick: true,
            endOnTick: true,
            min: 0,
            max: 0.8,
        },
        series: [{
            name: 'Probability of Default',
            data: data,
            color: 'white',
            lineWidth: 2,
            marker: { enabled: false }
        }],
        credits: { enabled: false },
        legend: { enabled: false }
    });

}

// Function to generate the data for the debt level chart.
function generate_debt_chart() {
    const data = [];
    current_ww_prob = parseFloat($("#wa_pd").text().replace("%", "")) / 100;
    total_debt = parseFloat($("#total_debt_sel").text().replace("%", "")) * 1000000;
    bitcoins = 20999999.9769;
    for (let i = 50; i <= 200; i += 10) {
        const valuation = total_debt * 1000 * (i) * current_ww_prob / bitcoins
        data.push([valuation, i]);
    }

    // Create the debt level chart.
    Highcharts.chart('debt-level-chart', {
        chart: {
            type: 'spline',
            backgroundColor: 'transparent'
        },
        title: {
            text: 'Bitcoin Valuation by Debt Levels changes',
            style: { fontSize: '14px', color: 'white' }
        },
        yAxis: {
            title: { text: 'Debt Level (% of current levels)' },
            labels: {
                formatter: function () { return this.value + '%'; },
                style: { color: 'white' }
            },
            gridLineColor: '#444',
            gridLineWidth: 1,
            startOnTick: true,
            endOnTick: true,
            min: 50,
            max: 200,

        },
        xAxis: {
            title: { text: 'Bitcoin Price' },
            labels: { style: { color: 'white' } },
            gridLineColor: '#444',
            gridLineWidth: 1,
            minorGridLineColor: '#444',
            minorGridLineWidth: 1,
            minorTickInterval: 'auto'
        },
        series: [{
            name: 'Debt Level',
            data: data,
            color: 'white',
            lineWidth: 2,
            marker: { enabled: false }
        }],
        credits: { enabled: false },
        legend: { enabled: false }
    });


}


