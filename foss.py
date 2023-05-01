import os
import json
import requests
from bs4 import BeautifulSoup
import pandas as pd
from backend.config import basedir, home_dir
from backend.utils import pickle_it, file_created_today
from pricing_engine.engine import historical_prices
from concurrent.futures import ThreadPoolExecutor, as_completed

# Bitcoin Valuation Model
# based on Greg Foss model

# See page 25 of the following paper
# 3.5 Bitcoin is default insurance...
paper_url = 'https://rockstarinnercircle.com/wp-content/uploads/2021/04/Why-Every-Fixed-Income-Investor-Needs-To-Consider-Bitcoin-As-Portfolio-Insurance.pdf'

total_bitcoins = 20999999.9769  # Total number of bitcoins that will ever exist


# First step is to get a table of Credit Default Swap (CDS) rates
def fetch_cds_table():
    # try to load file
    filename = os.path.join(home_dir, 'cds_table.pkl')
    # Check if file is fresh
    if file_created_today(filename):
        data = pickle_it('load', filename)
        return (data)

    url = 'http://www.worldgovernmentbonds.com/sovereign-cds/'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    table = soup.find('table')

    # Manually adjust the headers to correctly represent the data
    headers = [
        'index',
        'Country',
        'Rating',
        '5Y CDS',
        'Var 1m',
        'Var 6m',
        'PD (*)',
        'Date',
    ]

    rows = []
    for row in table.find_all('tr')[2:]:
        cells = row.find_all('td')
        cell_values = [cell.text.strip() for cell in cells]

        # Add empty cells if needed
        while len(cell_values) < len(headers):
            cell_values.append("")

        rows.append(cell_values)

    cds_df = pd.DataFrame(rows, columns=headers)
    pickle_it('save', filename, cds_df)
    return cds_df


# Now let's fetch the debt data from these countries
def debt_table():
    # Load json file
    filename = os.path.join(basedir, 'static/json_files/debt_data.json')
    with open(filename, 'r') as handle:
        debt_data = json.load(handle)
    return debt_data


def debt_as_gdp():
    # Try to load the data
    filename = os.path.join(home_dir, 'debt_gdp_data.pkl')
    # check if fresh, if so, load it
    if file_created_today(filename):
        data = pickle_it('load', filename)
        return (data)

    # If not, let's fetch it
    # source:
    url = "https://stats.oecd.org/sdmx-json/data/DP_LIVE/.GGDEBT.../OECD?contentType=csv&detail=code&separator=comma&csv-lang=en"

    debt_gdp_data = pd.read_csv(url)
    debt_gdp_data = debt_gdp_data.loc[debt_gdp_data['MEASURE'] == 'MLN_USD']

    pickle_it('save', 'debt_gdp_data.pkl', debt_gdp_data)

    return debt_gdp_data


def gdp_data():
    # Try to load the data
    filename = os.path.join(home_dir, 'gdp_data.pkl')
    # check if fresh, if so, load it
    if file_created_today(filename):
        data = pickle_it('load', filename)
        return (data)

    # If not, let's fetch it
    # source:
    url = "https://stats.oecd.org/sdmx-json/data/DP_LIVE/.GDP.../OECD?contentType=csv&detail=code&separator=comma&csv-lang=en"

    gdp_data = pd.read_csv(url)
    gdp_data = gdp_data.loc[gdp_data['MEASURE'] == 'MLN_USD']

    pickle_it('save', 'gdp_data.pkl', gdp_data)

    return gdp_data


# Build the dataframe
def foss_model():
    cds_data = fetch_cds_table()
    debt_data = debt_table()

    # Create a dataframe from the debt_data dictionary
    debt_ul_df = pd.DataFrame(debt_data).T.reset_index().rename(
        columns={'index': 'Country'})
    debt_ul_df['Total_Debt_UL'] = debt_ul_df[
        'total government debt Tri'] + debt_ul_df[
            'unfunded liabilities (in trillions)']

    # Merge CDS data with the debt_ul_df
    cds_data['Country'] = cds_data['Country'].str.strip()
    cds_data = cds_data[['Country', '5Y CDS']]
    cds_data['5Y CDS'] = pd.to_numeric(cds_data['5Y CDS'], errors='coerce')

    # Merge the dataframes
    final_df = debt_ul_df.merge(cds_data, on='Country')

    # Calculate the valuation model
    final_df['Valuation_Model'] = final_df['Total_Debt_UL'] * final_df[
        '5Y CDS'] / 10000 * 1000000000000  # so many fucking zeros -- scary

    final_df['BTC_Model'] = final_df['Valuation_Model'] / total_bitcoins

    return final_df


def get_data(ticker):
    data = historical_prices(ticker)
    if data is None:
        data = pd.DataFrame()
    data = data.dropna()
    return {ticker: historical_prices(ticker)}


# Get Domestic and International Debt Data from the
# FRED API - This can be checked once a day only
def get_FRED_debt():
    debt = debt_table()
    ticker_list = []
    for country, value in debt.items():
        ticker_list.append('FRED:' +
                           value["total government debt FRED (domestic)"])
        ticker_list.append('FRED:' +
                           value["total government debt FRED (international)"])
    # Grab prices as a thread... There are multiple.
    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(get_data, ticker): ticker
            for ticker in ticker_list
        }

        results = []

        for future in as_completed(futures):
            results.append(future.result())

        # Collapse the list of dictionaries into one dictionary
        output = {}
        for r in results:
            for key, value in r.items():
                if value is None:
                    value = pd.DataFrame()
                output[key] = value

    return output
