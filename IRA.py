from backend.parseNumbers import parseNumber
from flask import (Blueprint, render_template, current_app, redirect, flash,
                   url_for, request)

from routes.orangenomics.IRA_helpers import (load_competitor_data, load_ira,
                                             ira_run_comparison,
                                             ira_run_waterfall,
                                             return_json_name)

ira = Blueprint('ira', __name__)

# Minimum TemplateData used for render_template in all routes
# This ensures FX and current_app are sent to the render page
# at all times

templateData = {"title": "Nakamoto Portfolio", "current_app": current_app}


# list all IRA services available
@ira.route("/ira/list", methods=['GET', 'POST'])
def ira_list():
    templateData['title'] = "IRA Competitors List"
    templateData['ira_list'] = load_competitor_data(html=True)
    return (render_template('orangenomics/ira/ira_list.html', **templateData))


# Run the comparison
@ira.route("/ira/comparison", methods=['GET', 'POST'])
def ira_comp():
    templateData['title'] = "IRA Competitors Comparison"
    templateData['ira_list'] = load_competitor_data()
    templateData['ira_json'] = load_competitor_data(json_export=True)
    templateData['ira_list_html'] = load_competitor_data(html=True)
    ira = request.args.get("ira")
    btc = request.args.get("btc")
    cash = request.args.get("cash")
    btc_chg = request.args.get("btc_chg")
    years = request.args.get("years")
    contribution = request.args.get("contribution")
    return_json = request.args.get('return_json')
    errors = 0

    if ira == 'This is a new IRA' or ira == 'Choose One' or ira is None:
        errors += 1
        flash("You must select an IRA service provider", "warning")

    if ira is not None:

        try:
            contribution = parseNumber(contribution)
            if contribution == '' or contribution is None or contribution == '-':
                contribution = 0
        except Exception:
            errors += 1
            flash("You must enter a valid contribution amount", "warning")

        try:
            if btc == '' or btc is None or btc == '-':
                btc = 0
            btc = parseNumber(btc)
        except Exception:
            errors += 1
            flash("You must enter a valid number of Bitcoins", "warning")

        try:
            if btc_chg == '' or btc_chg is None or btc_chg == '-':
                btc_chg = 0
                flash("No BTC change provided, assuming price will be flat.",
                      "info")
            btc_chg = 1 + (parseNumber(btc_chg) / 100)
        except Exception:
            errors += 1
            flash("You must enter a valid percentage change", "warning")

        try:
            if years == '' or years is None or years == '-':
                years = 10
            years = parseNumber(years)
        except Exception:
            errors += 1
            flash("You must enter a valid number of years", "warning")

        try:
            if cash == '' or cash is None or cash == '-':
                cash = 0
            cash = parseNumber(cash)
        except Exception:
            errors += 1
            flash("You must enter a valid cash position", "warning")

        if cash == 0 and btc == 0:
            errors += 1
            flash("Either a BTC or Cash position needs to be entered",
                  "warning")

    # If an IRA is sent as argument, run the comparison
    if ira is not None and errors == 0:

        templateData['inputs'] = {
            'ira': ira,
            'btc': btc,
            'cash': cash,
            'btc_chg': btc_chg,
            'years': years,
            'contribution': contribution
        }
        templateData['results'] = ira_run_comparison(ira, btc, cash, years,
                                                     btc_chg, contribution)

        # Run waterfall with these results
        waterfall = ira_run_waterfall(templateData)
        templateData['results']['chart_data'] = {'waterfall': waterfall}
        templateData['results']['ira_json_name'] = return_json_name(ira)

        if templateData['results'] == None:
            flash("Could not run analysis. Try again.", "danger")
            return (render_template('orangenomics/ira/ira_comp.html',
                                    **templateData))

        if return_json is not None:
            return (templateData['results'])

        return (render_template('orangenomics/ira/results.html',
                                **templateData))

    return (render_template('orangenomics/ira/ira_comp.html', **templateData))


# API to get IRA provider information
@ira.route("/ira/api/details", methods=['GET', 'POST'])
def ira_details():
    ira = request.args.get("ira")
    ira_details = load_ira(ira)
    return ira_details


@ira.route('/apps/ira/ira_client', methods=['GET', 'POST'])
def ira_client():
    templateData['title'] = "IRA Client Calculator"
    templateData['ira_list'] = load_competitor_data()
    return render_template('orangenomics/main/ira_client.html', **templateData)


@ira.route('/apps/ira/ira_client_basic', methods=['GET', 'POST'])
def ira_client_basic():
    templateData['title'] = "IRA Client Calculator - Landing Page"
    return render_template('orangenomics/main/ira_client_basic.html',
                           **templateData)
