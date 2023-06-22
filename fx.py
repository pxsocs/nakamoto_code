import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
from backend.decorators import MWT
from backend.parseNumbers import parseNumber
from backend.config import basedir, home_dir
from backend.utils import pickle_it, file_created_today, compute_hash
import yfinance as yf


# Gets a list of all the FXs
def get_fx_list():
    filename = os.path.join(basedir, 'static/json_files/currency.json')
    with open(filename) as fx_json:
        fx_list = json.load(fx_json)
    return (fx_list)


# Gets a list of currencies
# This grabs the historical DF
# ex: ['EURUSD=X', 'GBPUSD=X', 'USDBRL=X']
def fx_rate(fx_list):

    # Check if item is 3 letters only. If so, add the USDnnn=X
    fx_list = [x if len(x) > 3 else 'USD' + x + '=X' for x in fx_list]

    # But also create a list with just the 3 letters
    fx_list_3 = [x[3:6] for x in fx_list]

    if 'BTC-USD' not in fx_list:
        # append it
        fx_list.append('BTC-USD')

    # Sort the list
    sorted_fx_list = sorted(fx_list)
    arg_list = [sorted_fx_list]
    hash_id = compute_hash(arg_list)
    filename = 'tmp_port/' + hash_id + '.portfolio'
    filename = os.path.join(home_dir, filename)

    # Check if this file was already created today.
    # if so load it and return it. Unless force is set to True.
    if file_created_today(filename, 24):
        data = pickle_it('load', filename)
        return (data)

    forex_data = yf.download(fx_list, group_by='ticker')

    # Find the first and last date in the original index
    first_date = forex_data.index.min()
    last_date = forex_data.index.max()

    # Create a new index that includes every day in this range
    all_dates = pd.date_range(start=first_date, end=last_date, freq='D')

    # Reindex forex_data to include all dates, forward filling, then back filling any gaps
    forex_data = forex_data.reindex(all_dates).ffill().bfill()

    pickle_it('save', filename, forex_data)

    return forex_data


def find_fx_ondate(date, fx, df_rates):
    # Find this date in the rates dataframe
    closest_date = df_rates.index.asof(date)
    return df_rates.loc[closest_date][fx]['Close']


def fxsymbol(fx, output='symbol'):
    # Gets an FX 3 letter symbol and returns the HTML symbol
    # Sample outputs are:
    # "EUR": {
    # "symbol": "",
    # "name": "Euro",
    # "symbol_native": "",
    # "decimal_digits": 2,
    # "rounding": 0,
    # "code": "EUR",
    # "name_plural": "euros"
    fx_list = get_fx_list()
    try:
        return fx_list[fx][output]
    except KeyError:
        if output == 'all':
            return fx_list[fx]
        return fx


# Background job to get the big mac data
# from the economist - no reason to run this more
# than once a day
def get_big_mac_data():
    filename = 'big-mac-df.pkl'
    file = os.path.join(home_dir, filename)
    if file_created_today(file):
        return (pickle_it('load', filename))

    url = "https://github.com/theeconomist/big-mac-data/releases/latest/download/big-mac-full-index.csv"
    df = pd.read_csv(url, parse_dates=['date'])

    # Save the file
    pickle_it('save', filename, df)

    return (df)


# How many bigmacs you can buy in each country
# This is the latest data for all countries
def big_sat_index():
    return_dict = {}
    df = get_big_mac_data()

    # Get the range of dates in big mac index
    return_dict['start_date'] = df['date'].min()
    return_dict['end_date'] = df['date'].max()

    # Get the list of FX to download -- these are the fx in the big mac index
    fx_list = df['currency_code'].unique()

    # Remove unreliable currencies
    unreliable = ['AZN', 'LBP', 'SYP', 'VEF', 'ZWD', 'ZWL', 'VES']
    fx_list = [x for x in fx_list if x not in unreliable]
    # Remove from the df as well
    df = df[~df['currency_code'].isin(unreliable)]

    return_dict['fx_list'] = fx_list

    # Download fx data
    df_rates = fx_rate(fx_list)

    # Update the fx rates with historical data
    df['fx_rate'] = np.nan
    df['btc_price'] = np.nan

    # Iterate over df to fill the 'fx_rate' column
    for i, row in df.iterrows():
        # Azerbaijan has no fx rate - remove
        if row['currency_code'] == 'AZN':
            continue
        # Reformat the currency code
        currency_code = 'USD' + row['currency_code'] + '=X'
        date = row['date']
        # Find the fx
        fx = find_fx_ondate(date, currency_code, df_rates)
        btc = find_fx_ondate(date, 'BTC-USD', df_rates)
        # Update orifinal df
        df.at[i, 'fx_rate'] = fx
        df.at[i, 'btc_price'] = btc

    # Now get the latest date
    max_df = df.loc[df['date'] == df['date'].max()]
    today = datetime.today()
    new_rows = []
    for i, row in max_df.iterrows():
        # Azerbaijan has no fx rate - remove
        if row['currency_code'] == 'AZN':
            continue
        # Reformat the currency code
        currency_code = 'USD' + row['currency_code'] + '=X'
        fx = find_fx_ondate(today, currency_code, df_rates)
        btc = find_fx_ondate(today, 'BTC-USD', df_rates)
        new_row = {
            'date': today,
            'iso_a3': row['iso_a3'],
            'currency_code': row['currency_code'],
            'name': row['name'],
            'local_price': row['local_price'],
            'fx_rate': fx,
            'btc_price': btc,
        }
        new_rows.append(new_row)

    df_new = pd.DataFrame(new_rows)
    df = pd.concat([df, df_new], ignore_index=True)

    # Fill USD FX Rate with 1.00
    df.loc[df['currency_code'] == 'USD', 'fx_rate'] = 1.00

    # Make all necessary calculations now
    df['price_usd'] = df['local_price'] / df['fx_rate']
    df['price_btc'] = df['price_usd'] / df['btc_price']
    df['price_sats'] = df['price_btc'] * 100000000
    reference_sats = 100000  # 1 million sats buys how many big macs?
    df['big_sats'] = reference_sats / df['price_sats']

    return_dict['reference_sats'] = reference_sats
    return_dict['df'] = df

    return return_dict
