const sources = [
    'FRED', 'twelvedata', 'alphavantage', 'alphavantage_global',
    'cryptocompare', 'yahoo', 'fmp'
];

$(document).ready(function () {
    $("#spinner").hide();
    const $searchField = $('#searchField');
    const $searchResults = $('#searchResults');
    let searchTimeout;

    $searchField.on('input', function () {
        const query = $(this).val().trim();

        if (!query) {
            $searchResults.hide();
            return;
        }

        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }

        searchTimeout = setTimeout(() => {
            search(query, function (results) {
                $searchResults.html(renderResults(results));
                $searchResults.show();
            });
        }, 100); // Adjust the delay as needed
    });

    // $searchResults.on('click', '.search-result-item', function () {
    //     const value = $(this).text();
    //     const symbol = $(this).data('symbol');
    //     $searchResults.hide();
    //     $searchField.val('Sending data... Please wait...');
    //     $searchField.prop('disabled', true);
    //     $('#searchButton').data('chart-symbol', symbol); // Update the search button with the data-chart-symbol property
    //     data = encodeURIComponent(value);
    //     const url = base_url() + `apps/asset_report?data=${data}`;
    //     window.open(url, '_self');
    // });

    $(document).on('click', function (event) {
        if (!$(event.target).closest('#searchField').length && !$(event.target).closest('#searchResults').length) {
            $searchResults.hide();
        }
    });
});



function search(query, callback) {
    if (query.length < 2) {
        $("#results").hide();
        return;
    }

    // Show spinner
    $("#spinner").show();

    let results = [];
    let sourcesCompleted = 0;

    sources.forEach(src => {
        $.ajax({
            url: `/api/search?query=${query}&src=${src}`,
            method: 'GET',
            dataType: 'json',
            success: function (response) {
                if (response && response.results) {
                    results = results.concat(response.results);
                } else {
                    console.error('Error: Invalid response format');
                }
            },
            error: function (error) {
                console.error('Error:', error);
            },
            complete: function () {
                sourcesCompleted++;
                if (sourcesCompleted === sources.length) {
                    // Hide spinner
                    $("#spinner").hide();
                    callback(results);
                }
            }
        });
    });
}

function renderResults(results) {
    if (!Array.isArray(results)) {
        console.error('Error: results is not an array');
        return '';
    }

    // Empty results
    if (results.length === 0) {
        return '<div class="search-result-item">No results found</div>';
    } else {

        return results.map(result => `
    <div class="search-result-item" data-symbol="${result.symbol}">
${result.symbol} | ${result.name} | ${result.fx} | ${result.notes} | ${result.provider}
    </div>
  `).join('');
    }

}


