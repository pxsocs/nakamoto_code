$(document).ready(function () {
    console.log("00000080   01 04 45 54 68 65 20 54  69 6D 65 73 20 30 33 2F   ..EThe Times 03/");
    console.log("00000090   4A 61 6E 2F 32 30 30 39  20 43 68 61 6E 63 65 6C   Jan/2009 Chancel");
    console.log("000000A0   6C 6F 72 20 6F 6E 20 62  72 69 6E 6B 20 6F 66 20   lor on brink of ");
    console.log("000000B0   73 65 63 6F 6E 64 20 62  61 69 6C 6F 75 74 20 66   second bailout f");
    console.log("000000C0   6F 72 20 62 61 6E 6B 73  FF FF FF FF 01 00 F2 05   or banksÿÿÿÿ..ò.");

    satoshi_refresh();

    BTC_price();
    mempool_refresh();
    // Updates BTC Price every 20 seconds
    window.setInterval(function () {
        BTC_price();
    }, 20000);
    // Refresh Mempool every 1 minutes
    window.setInterval(function () {
        mempool_refresh();
    }, 600000);


    // Principal Action
    const icon = $('#icon');
    const hi_principal = $('#hi_principal');
    let hoverTimeout;
    icon.on('mouseenter', () => {
        hoverTimeout = setTimeout(() => {
            hi_principal.addClass('visible');
        }, 10000); // 10 seconds
    });
    icon.on('mouseleave', () => {
        clearTimeout(hoverTimeout);
        if (hi_principal.hasClass('visible')) {
            hi_principal.removeClass('visible');
        }
    });
    $(document).on('mousemove', () => {
        if (hi_principal.hasClass('visible')) {
            hi_principal.removeClass('visible');
        }
    });
    // End Principal Action


});

function mempool_refresh() {
    $.ajax({
        type: "GET",
        dataType: 'json',
        url: "https://mempool.space/api/blocks/tip/height",
        success: function (data) {
            $('#block_height').html("<span class='text-green'>" + data.toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 0, minimumFractionDigits: 0 }) + "</span>").fadeTo(100, 0.3, function () { $(this).fadeTo(500, 1.0); });
            halving = 840000
            blk = parseInt(data)
            blks = halving - blk
            days_left = parseInt(((blks) * 10 / 60 / 24))
            // find date that is days_left from now
            var d = new Date();
            d.setDate(d.getDate() + days_left);
            // Shorten date to MMM/DD/YY format
            d = d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });

            $('#halving').html("<span class='text-green'>" + blks.toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 0, minimumFractionDigits: 0 }) + " blocks left</span>").fadeTo(100, 0.3, function () { $(this).fadeTo(500, 1.0); });
            $('#days_to_halving').html("(~" + days_left.toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 0, minimumFractionDigits: 0 }) + " days to go)").fadeTo(100, 0.3, function () { $(this).fadeTo(500, 1.0); });
            $('#time_halving').html("<span class='text-green'>" + d + "</span>").fadeTo(100, 0.3, function () { $(this).fadeTo(500, 1.0); });
        },
        error: function (xhr, status, error) {
            console.log("Error on fx request")
        }
    });
};


function BTC_price() {
    $.ajax({
        type: "GET",
        dataType: 'json',
        url: "/realtime_btc",
        success: function (data) {
            if ('cross' in data) {
                sats_price = 100000000 / parseFloat(data['btc_usd']);
                $('#sats_price').html("<span class='text-green'>" + sats_price.toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 0, minimumFractionDigits: 0 }) + " sats/$</span>").fadeTo(100, 0.3, function () { $(this).fadeTo(500, 1.0); });
                $('#btc_price').html("<span class='text-green'>$ " + data['btc_usd'].toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 0, minimumFractionDigits: 0 }) + "</span>").fadeTo(100, 0.3, function () { $(this).fadeTo(500, 1.0); });
            } else {
                console.log("Error on FX request -- missing info")
            }

        },
        error: function (xhr, status, error) {
            console.log("Error on fx request")
        }
    });
};


function satoshi_refresh() {
    $.ajax({
        type: 'GET',
        url: '/api/satoshi_quotes_json',
        dataType: 'json',
        success: function (data) {
            // Parse data
            $('#satoshi_loading').hide();
            $('#quote_section').show();
            $('#load_quote').html(data['text']);
            $('#load_source').html(data['medium']);
            $('#load_date').html(data['date']);
            $('#subject').html(data['category']);
            $('#refresh_button').html('Refresh');
            $('#refresh_button').prop('disabled', false);

        },
        error: function (xhr, status, error) {
            console.log(status);
            console.log(error);
            $('#alerts').html("<div class='small alert alert-danger alert-dismissible fade show' role='alert'>An error occured while refreshing data." +
                "<button type='button' class='close' data-bs-dismiss='alert' aria-label='Close'><span aria-hidden='true'>&times;</span></button></div>")
            $('#refresh_button').html('Refresh Error. Try Again.');
            $('#refresh_button').prop('disabled', false);
        }

    });

}
