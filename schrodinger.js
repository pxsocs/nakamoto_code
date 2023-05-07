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


    console.log("Ready to calculate fair value of Schrodinger's Bitcoin");

    document.querySelectorAll("[data-bs-toggle='collapse']").forEach(function (collapseBtn) {
        collapseBtn.addEventListener("click", function () {
            let icon = this.querySelector(".fa-angle-down, .fa-angle-up");

            if (icon) {
                if (icon.classList.contains("fa-angle-down")) {
                    icon.classList.remove("fa-angle-down");
                    icon.classList.add("fa-angle-up");

                    // Collapse other cards
                    document.querySelectorAll("[data-bs-toggle='collapse']").forEach(function (otherCollapseBtn) {
                        if (otherCollapseBtn !== collapseBtn) {
                            let otherIcon = otherCollapseBtn.querySelector(".fa-angle-down, .fa-angle-up");
                            if (otherIcon && otherIcon.classList.contains("fa-angle-up")) {
                                otherIcon.classList.remove("fa-angle-up");
                                otherIcon.classList.add("fa-angle-down");
                            }
                            let otherCollapseContent = document.getElementById(otherCollapseBtn.getAttribute("aria-controls"));
                            if (otherCollapseContent) {
                                otherCollapseContent.classList.remove("show");
                                otherCollapseContent.classList.add("collapse");
                            }
                        }
                    });
                } else {
                    icon.classList.remove("fa-angle-up");
                    icon.classList.add("fa-angle-down");
                }
            }
        });
    });

    const btc_coins = 20999999.9769

    // Load Base Case Scenario
    $.ajax({
        url: "/static/json_files/s_base.json",
        dataType: "json",
        success: function (data) {
            loadScenario(data);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.error("Error loading JSON: " + textStatus + " - " + errorThrown);
        }
    });


    // Load Asset Data
    $.ajax({
        url: "/static/json_files/asset_data.json",
        dataType: "json",
        success: function (data) {
            window.asset_data = data;
            buildTable();
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.error("Error loading JSON: " + textStatus + " - " + errorThrown);
        }
    });


    // New function to load scenario from URL
    const loadScenarioFromUrl = (url) => {
        $.ajax({
            url: url,
            dataType: "json",
            success: function (data) {
                loadScenario(data);
            },
            error: function (jqXHR, textStatus, errorThrown) {
                console.error("Error loading JSON: " + textStatus + " - " + errorThrown);
            }
        });
    };

    // Load scenarios on button click
    $("#base-btn").click(function () {
        $("#bullish-btn, #bearish-btn, #hyper-btn").removeClass('selected-scenario');
        $("#base-btn").addClass('selected-scenario');
        loadScenarioFromUrl("/static/json_files/s_base.json");
    });

    $("#bullish-btn").click(function () {
        $("#base-btn, #bearish-btn, #hyper-btn").removeClass('selected-scenario');
        $("#bullish-btn").addClass('selected-scenario');
        loadScenarioFromUrl("/static/json_files/s_bullish.json");
    });

    $("#bearish-btn").click(function () {
        $("#bullish-btn, #base-btn, #hyper-btn").removeClass('selected-scenario');
        $("#bearish-btn").addClass('selected-scenario');
        loadScenarioFromUrl("/static/json_files/s_bearish.json");
    });

    $("#hyper-btn").click(function () {
        $("#bullish-btn, #base-btn, #bearish-btn").removeClass('selected-scenario');
        $("#hyper-btn").addClass('selected-scenario');
        loadScenarioFromUrl("/static/json_files/s_hyper.json");
    });

    fetch("/realtime_btc")
        .then((response) => response.json())
        .then((data) => {
            $("#btc-price").text(formatNumber(data.btc_usd, 0, '$ '));
            window.btcPrice = data.btc_usd;
            $("#btc-fairvalue-mkt").text(formatNumber(data.btc_usd * btc_coins / 1000000000, 0, '$ ', 'B'));
            updateBtcFairValue();
            const data_api = collectData();
            sendDataToAPI(data_api).catch((error) => console.error(error));
        });

    createImpliedProbabilitiesTable();

    const data = collectData();
    sendDataToAPI(data).catch((error) => console.error(error));

    // Calculates Fair Value of Schrodinger's Bitcoin
    const calculateFairValue = (marketValue, monetaryPremium, captureProbability, timeToCapture, discountRate) => {
        return (marketValue * monetaryPremium * captureProbability) / Math.pow(1 + discountRate, timeToCapture);
    };

    const updateAssetBtcFv = (asset) => {
        const marketValue = parseFloat($(`#market-value-${asset}`).val()) * 1e12; // Convert to trillions
        const monetaryPremium = parseFloat($(`#monetary-premium-${asset}`).val()) / 100;
        const captureProbability = parseFloat($(`#prob-capture-${asset}`).val()) / 100;
        const timeToCapture = parseFloat($(`#time-to-capture-${asset}`).val());
        const discountRate = parseFloat($(`#discount_rate`).val()) / 100;
        const BTCModelResult = parseFloat($(`#btc-fairvalue-price`).text().replace('$', '').replace(',', ''));

        const fairValue = calculateFairValue(marketValue, monetaryPremium, captureProbability, timeToCapture, discountRate);
        $(`#${asset}_btc_fv`).text(formatNumber(fairValue, 0, '$ '));
        $(`#${asset}_btc_price`).text(formatNumber((fairValue / btc_coins), 0, '$ '));

        updateBtcFairValue();
    };

    const updateBtcFairValue = () => {
        console.log("here")
        let totalFairValue = 0;
        assets.forEach(asset => {
            n = $(`#${asset}_btc_fv`).text().replace(/[$,]/g, '')
            if (n != '-') {
                totalFairValue += parseFloat(n);
            }
        });
        // Also add current BTC FV
        totalFairValue += btcPrice * btc_coins;
        console.log(totalFairValue)
        console.log(totalFairValue / btc_coins)
        $("#btc-fairvalue").text(formatNumber(totalFairValue / 1000000000, 0, '$ ', 'B'));
        $("#btc-fairvalue-price").text(formatNumber((totalFairValue / btc_coins), 0, '$ '));
        $("#assets-total").text(formatNumber((totalFairValue / btc_coins), 0, '$ '));

        // Update percentages
        assets.forEach(asset => {
            asset_btc_price = parseFloat($(`#${asset}_btc_price`).text().replace(/[$,]/g, ''));
            $(`#${asset}_btc_perc`).text(formatNumber((asset_btc_price / (totalFairValue / btc_coins) * 100), 2) + '%');
        });

        $("#btc_current_price").text(formatNumber((btcPrice), 0, '$ '));
        $("#btc_btc_perc").text(formatNumber((btcPrice / (totalFairValue / btc_coins) * 100), 2) + '%');

        updateUpside();
        updateImpliedProbabilities();
        buildTable();
    };

    const updateSliderLabel = (element, outputElement) => {
        outputElement.text(element.val() + "%");
    };

    // Initial calculations for all assets
    assets.forEach(asset => {
        updateAssetBtcFv(asset);
    });

    $('#discount_rate').on('input', () => {
        const data = collectData();
        sendDataToAPI(data).catch((error) => console.error(error));
    });

    assets.forEach((asset) => {
        const inputIds = [
            `market-value-${asset}`,
            `monetary-premium-${asset}`,
            `prob-capture-${asset}`,
            `time-to-capture-${asset}`,
        ];

        inputIds.forEach((id) => {
            $(`#${id}`).on('input', () => {
                const data = collectData();
                sendDataToAPI(data).catch((error) => console.error(error));
            });
        });
    });



    // Event listeners for input changes
    $('#discount_rate').on('change', function () {
        $('#discount_rate').val(formatNumber(parseFloat($(this).val()), 2) + '%');
    });
    assets.forEach(asset => {
        $(`#discount_rate`).on('input', () => updateAssetBtcFv(asset));
        $(`#market-value-${asset}`).on('input', () => updateAssetBtcFv(asset));
        $(`#monetary-premium-${asset}`).on('input', function () {
            updateSliderLabel($(this), $(`#mp-${asset}`));
            updateAssetBtcFv(asset);
        });
        $(`#prob-capture-${asset}`).on('input', function () {
            updateSliderLabel($(this), $(`#pr-${asset}`));
            updateAssetBtcFv(asset);
        });
        $(`#time-to-capture-${asset}`).on('input', function () {
            updateAssetBtcFv(asset);
        });
    });
});


function updateUpside() {
    const fairValuePrice = $(`#btc-fairvalue-price`).text().replace(/[$,]/g, '')
    const currentPrice = $(`#btc-price`).text().replace(/[$,]/g, '')

    if (!isNaN(fairValuePrice) && !isNaN(currentPrice)) {
        const percentage = (fairValuePrice / currentPrice);
        if (percentage > 1) {
            $('#btc-upside').html("<i class='fa-solid fa-circle-arrow-up fa-sm text-success'></i>&nbsp;<strong class='text-success'>" + formatNumber(percentage, 0) + 'x</strong>')
        } else {
            $('#btc-upside').html("<i class='fa-solid fa-circle-arrow-down fa-sm  text-danger'></i>&nbsp;" + formatNumber(percentage, 0) + 'x')
        }
    }
}



function updateImpliedProbabilities() {

    // Calculates Fair Value of Schrodinger's Bitcoin
    const calculateFairValue = (marketValue, monetaryPremium, captureProbability, timeToCapture, discountRate) => {
        return (marketValue * monetaryPremium * captureProbability) / Math.pow(1 + discountRate, timeToCapture);
    };

    const btc_coins = 20999999.9769
    let btcMcap = parseFloat($("#btc-price").text().replace(/[$,]/g, "")) * btc_coins;
    let discountRate = parseFloat($("#discount_rate").val().replace(/[%]/g, "")) / 100;
    const tableBody = $("#implied-probabilities-table-body");
    assets.forEach((asset) => {
        let marketValue = parseFloat($(`#market-value-${asset}`).val().replace(/[$,]/g, "")) * 1000000000000;
        let mp = parseFloat($(`#monetary-premium-${asset}`).val()) / 100;
        let ttc = parseFloat($(`#time-to-capture-${asset}`).val());
        let impliedProb = 0;


        // Calculate implied probability of monetization
        if (marketValue > 0 && mp > 0 && ttc > 0) {
            const fairValue_at_100 = calculateFairValue(marketValue, mp, 1, ttc, discountRate);
            impliedProb = btcMcap / fairValue_at_100;
        }
        // Update the table with the new data
        $(`#implied-probability-${asset}`).text(formatNumber(impliedProb * 100, 0, '', '%'));

    });
}

// Function to create the implied probability of monetization table
function createImpliedProbabilitiesTable() {
    const tableBody = $("#implied-probabilities-table-body");

    assets.forEach((asset) => {
        const row = `
      <tr>
        <td class='text-start'>${asset}</td>
        <td class='text-center' id="implied-mp-${asset}"></td>
        <td class='text-center' id="implied-ttc-${asset}"></td>
        <td class='text-end' ></td>
      </tr>
    `;
        tableBody.append(row);
    });
}



function collectData() {
    const discountRateValue = parseFloat($('#discount_rate').val().replace('%', '')) / 100;
    const cryptoData = {};

    assets.forEach((asset) => {
        const mktCapTrillions = parseFloat($(`#market-value-${asset}`).val());
        const percMonetary = parseFloat($(`#monetary-premium-${asset}`).val()) / 100;
        const probCapture = parseFloat($(`#prob-capture-${asset}`).val()) / 100;
        const timeCapture = parseFloat($(`#time-to-capture-${asset}`).val());

        cryptoData[asset] = {
            mkt_cap_trillions: mktCapTrillions,
            perc_monetary: percMonetary,
            prob_capture: probCapture,
            time_capture: timeCapture,
        };
    });

    return {
        crypto: cryptoData,
        discount_rate: {
            value: discountRateValue,
        },
    };
}

async function sendDataToAPI(data) {
    const apiUrl = '/api/simulate_fv';
    try {
        const response = await $.ajax({
            url: apiUrl,
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
        });
        drawPVChart(response);
    } catch (error) {
        console.error(`Error sending data to the API: ${error.message} ${error.status} ${error.statusText}`);
    }
}

function loadScenario(data) {
    // Load data into input fields for each asset
    $.each(data.crypto, function (asset, value) {
        $("#market-value-" + asset).val(value.mkt_cap_trillions);
        $("#monetary-premium-" + asset).val(value.perc_monetary * 100);
        $("#prob-capture-" + asset).val(value.prob_capture * 100);
        $("#time-to-capture-" + asset).val(value.time_capture);
    });
    $("#discount_rate").val(data.discount_rate.value * 100 + "%").trigger("input");
}

function buildTable() {
    dataTable = collectData().crypto;

    $("#asset-table").html('')
    if (window.asset_data == undefined) {
        return
    }
    $.each(dataTable, function (asset, value) {
        const tableBox = `
    <div class="asset-box">
        <div class='asset-text' style="padding-top:10px;">
            <div class="d-grid gap-2" style="padding-bottom: 10px;">
                <button
                    class="btn btn-outline-light float-start text-white nolink"
                    type="button"
                    data-bs-toggle="collapse"
                    data-bs-target="#collapse-${asset}"
                    aria-expanded="false"
                    aria-controls="collapse-${asset}"
                    >
                    ${titleCase(asset.replace("_", " "))}</span>
                    <span class='float-end'><i class="
                    ${window.asset_data[asset]['icon']} text-white"></i>
                </button>
            </div>
            Mkt Cap <strong class="float-end">
            ${value.mkt_cap_trillions} Tri</strong><br>
            Monetary Prem. <strong class="float-end">
            ${formatNumber(value.perc_monetary * 100, 0)}%</strong><br>
            Probab. Capture <strong class="float-end">
            ${formatNumber(value.prob_capture * 100, 0)}%</strong><br>
            Time to Capture <strong class="float-end">
            ${formatNumber(value.time_capture, 0)} yrs</strong><br>
            Imp. Prob. (*)
            <strong class="float-end"><span id="implied-probability-${asset}"></span></strong><br>
        </div>
    </div>
        `;


        // Append the asset box to the table
        $("#asset-table").append(tableBox);
    });

    const infoBox = `
        <div style="padding-top:10px; text-align: left;">
            <span class="text-small">
                (*) these are the probabilities of success implied
                in each asset so this asset
                <strong class='border-bottom'>by itself</strong>
                would justify the current BTC price.
                While keeping all other assumptions constant.
                </span>
        </div>

        `;


    $("#asset-table").append(infoBox);

}
