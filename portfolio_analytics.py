import concurrent.futures
import os
import json
from telnetlib import SE
from unittest import result
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import numpy as np
from pandas.util import hash_pandas_object
from flask import current_app, flash
from sqlalchemy import true
from time import time
import riskfolio as rp
import yfinance as yf
from pricing_engine.engine import historical_prices, get_yf, get_risk_free_rate
from backend.ansi_management import jformat
from backend.utils import (df_col_to_highcharts, pickle_it, safe_filename,
                           file_created_today, delete_old_files)
from backend.config import home_dir, basedir
from backend.decorators import MWT, timing
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import base64
from io import BytesIO
import matplotlib.pyplot as plt

# portfolios come as a list of tuples
# portfolio = [("BTC", 0.5), ("AAPL", 0.5)]

# tickers come as a list of tuples
# tickers = [['BTC', 'Bitcoin'], ['AAPL', 'Apple Inc'], ['', '']]


# =====================
# MAIN RETURN METHOD
# =====================
@MWT(timeout=6000)
def portfolio_analysis(portfolio,
                       tickers,
                       allocations=[0],
                       rebalance=None,
                       start_date=None,
                       end_date=None,
                       window=30,
                       fx='USD'):
    """
    Analyzes the portfolio and returns a dictionary of the analysis.
    receives portfolio and tickers
    starts threads to generate the analytics

    Note:
    What needs to be returned here
    METADATA:
        - start and end dates
        - allocations
        - portfolio
        - tickers
        - rebalance
    ASSETS:
        - all tickers
        - nav and price for each ticker
        - stats for each ticker
    PORTFOLIOS:
        - allocations (set of portfolios)
        - nav for all portfolios
        - stats for each portfolio
    CHARTS:
        - specific data for charts (pie, nav, etc)
    """
    analysis = {}
    # ---------------------
    # METADATA
    # ---------------------
    # Gets all parameters that where sent into funcion and store
    # at metadata level
    if 0 not in allocations:
        allocations.append(0)

    analysis['METADATA'] = {
        'portfolio': portfolio,
        'tickers': tickers,
        'allocations': sorted(allocations),
        'rebalance': rebalance,
        'start_date': start_date,
        'end_date': end_date,
        'fx': fx
    }

    analysis['METADATA']['names'] = {}
    for element in tickers:
        analysis['METADATA']['names'][element[0]] = element[1]

    # Get tickers from portfolio (tickers list has ticker and name)
    ticker_list = [x[0] for x in portfolio]
    if 'BTC' not in ticker_list:
        ticker_list.append('BTC')
        analysis['METADATA']['names']['BTC'] = 'Bitcoin'

    analysis['METADATA']['ticker_list'] = ticker_list
    analysis['METADATA']['risk_free_rate'] = get_risk_free_rate(
        start_date, end_date)

    # ---------------------
    # Kick off allocation Threads
    # These should include most of the information needed for data below
    # ---------------------
    data = simulate_btc_allocations(allocations, portfolio, fx, start_date,
                                    end_date, rebalance)

    # get the dataframe from the zero allocation to BTC NAV
    for item in data:
        if item['allocation'] == 0:
            df = item['df']

    analysis['METADATA']['min_date'] = df.index.min()
    analysis['METADATA']['max_date'] = df.index.max()
    # ---------------------
    # ASSETS
    # ---------------------

    analysis['ASSETS'] = simulation_metadada(df)

    # ---------------------
    # PORTFOLIOS
    # ---------------------
    analysis['PORTFOLIOS'] = dict(sorted(portfolio_metadata(data).items()))

    # ---------------------
    # CHARTS
    # ---------------------
    # Some charts can also be placed under the tickers
    analysis['CHARTS'] = {}
    # Create Pie Chart data for current portfolio
    analysis['CHARTS']['pie_chart'] = pie_chart(portfolio, tickers)

    # Create statistic chart data for each ticker and for portfolios
    rfr = analysis['METADATA']['risk_free_rate']
    analysis['CHARTS']['stats_chart'] = {
        'assets': stats_charts(analysis, 'assets', rfr),
        'portfolio': stats_charts(analysis, 'portfolios', rfr)
    }

    # Temp - need to check later
    analysis['CHARTS']['nav_chart_data'] = df_col_to_highcharts(
        df, ['port_NAV'])

    analysis['CHARTS']['all_assets_data'] = price_charts(df)
    analysis['CHARTS']['all_portfolios_data'] = portfolios_charts(data)
    analysis['CHARTS']['scatter_charts'] = scatter_charts(data)
    analysis['CHARTS']['rolling_correlation'] = rolling_correlation_matrix(
        df, window)

    # Create a chart data for each allocation
    analysis['CHARTS']['allocation'] = {}
    tmp_alloc = {}
    for alloc in allocations:
        # get the dataframe from the zero allocation to BTC NAV
        for item in data:
            if item['allocation'] == alloc:
                all_df = item['df']
                tmp_alloc[alloc] = all_df
        analysis['CHARTS']['allocation'][alloc] = allocation_chart(
            all_df, ticker_list)

    analysis['METADATA']['total_return'] = metadata_returns(
        tmp_alloc, allocations, rebalance)

    # ---------------------
    # TABLES
    # ---------------------
    analysis['TABLES'] = {}
    analysis['TABLES']['ranked_returns'] = annual_return_table(df, ticker_list)
    analysis['TABLES']['color_map'] = color_map(ticker_list)
    analysis['TABLES']['correlation_matrix'] = correlation_matrix(df)

    return analysis


@MWT(timeout=6000)
def ticker_to_name(ticker, tickers):
    if ticker == 'BTC':
        return 'Bitcoin'
    for element in tickers:
        if element[0] == ticker:
            return element[1]
    return None


@MWT(timeout=6000)
def add_btc_allocation(portfolio, btc_allocation):
    """
    Adds a BTC allocation to the portfolio and keeps total allocation to 1.
    btc_allocation = 0-1 : a target BTC allocation
    """
    portfolio = reweight(portfolio, (1 - btc_allocation))
    portfolio.append(('BTC', btc_allocation))
    return portfolio


@MWT(timeout=6000)
def remove_btc_allocation(portfolio):
    for item in portfolio:
        if item[0] == 'BTC':
            portfolio.remove(item)
    return portfolio


@MWT(timeout=6000)
def reweight(portfolio, target=1):
    if portfolio is None:
        return None
    total = sum([x[1] for x in portfolio])
    portfolio = [(x[0], (x[1] * target) / total) for x in portfolio]
    return portfolio


@MWT(timeout=6000)
@timing
def get_prices(ticker, portfolio, start_date=None, end_date=None, fx='USD'):
    # Get this ticker's initial weight in portfolio
    ticker_weight = 0
    for element in portfolio:
        if element[0] == ticker:
            ticker_weight = element[1]

    # gets a df with historical prices for the ticker
    prices = historical_prices(ticker, fx)

    # Makes some checks
    # is df empty?
    if prices.empty is True:
        prices[ticker + '_price'] = 0
        try:
            flash(
                f"prices for ticker {ticker} could not be downloaded -- excluded from NAV calculations",
                "warning")
        except Exception:
            print(
                f"prices for ticker {ticker} could not be downloaded -- excluded from NAV calculations"
            )
        return {
            'ticker': ticker,
            'df': prices,
            'save_nav': False,
            'ticker_weight': ticker_weight
        }

    # check if prices is a Series. If so, convert to dataframe
    if isinstance(prices, pd.Series):
        prices = prices.to_frame()

    # rename the column names so they are unique to this ticker
    prices = prices.rename(columns={'close_converted': ticker + '_price'})
    prices = prices[ticker + '_price']

    prices = prices.reset_index()
    prices['date'] = prices['date'].dt.date

    prices = prices.set_index(['date'])

    # Trim prices so it only includes from start to end date
    # Trim the dates from start to end if not None
    # greater than the start date and smaller than the end date
    if start_date is not None:
        if type(start_date) == datetime:
            prices = prices.loc[start_date.date():]
        else:
            prices = prices.loc[start_date:]

    if end_date is not None:
        if type(end_date) == datetime:
            prices = prices.loc[:end_date.date()]
        else:
            prices = prices.loc[:end_date]

    # Reindex so all dates are included
    prices = prices.asfreq('D')
    prices.index = prices.index.astype('datetime64[ns]')
    # Create an empty column to store quantities
    prices[ticker + '_quant'] = np.nan

    return {
        'ticker': ticker,
        'prices': prices,
        'save_nav': True,
        'ticker_weight': ticker_weight
    }


@MWT(timeout=6000)
@timing
def create_nav(portfolio,
               force=False,
               fx='USD',
               start_date=None,
               end_date=None,
               btc_allocation=0,
               rebalance=None):
    """
    Returns a df with daily NAV for the portfolio.
    tickers = [['BTC', 'Bitcoin'], ['AAPL', 'Apple Inc'], ['', '']]
    portfolio = [("BTC", 0.5), ("AAPL", 0.5)]
    force = true does not use cache
    fx = 'USD'
    start_date = '2018-01-01'
    end_date = '2018-12-31'
    btc_allocation = [0-1]
    """

    # Create a unique identifier for this NAV so it may be
    # loaded again later - NAV creation can be time consuming
    save_p = sorted(portfolio)
    filename = 'tmp_port/' + safe_filename(
        str(save_p) + '_BTC' + str(btc_allocation)) + '_' + fx + str(
            start_date) + str(end_date) + '.portfolio'
    filename = os.path.join(home_dir, filename)

    # Check if this file was already created today.
    # if so load it and return it. Unless force is set to True.
    if force is False and file_created_today(filename):
        nav = pickle_it('load', filename)
        return (nav)

    # Create a new NAV
    save_nav = True
    ticker_list = [x[0] for x in portfolio]

    # Include Bitcoin price
    if 'BTC' not in ticker_list:
        ticker_list.append('BTC')

    # Make sure portfolio is balanced to 100
    portfolio = reweight(portfolio, 1)

    # Include Bitcoin allocation
    if btc_allocation != 0:
        portfolio = remove_btc_allocation(portfolio)  # remove BTC allocation
        portfolio = add_btc_allocation(portfolio, btc_allocation)

    # Create empty df for NAV
    dailynav = pd.DataFrame(columns=['date'])

    # 1. get prices for each ticker and include into a df
    # Using ThreadPoolExecutor to run threads concurrently
    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(get_prices, ticker, portfolio, start_date,
                            end_date, fx): ticker
            for ticker in ticker_list
        }

        merged_dfs = []

        for future in as_completed(futures):
            merged_dfs.append(future.result())

        # Sort by weights
        merged_dfs = sorted(merged_dfs,
                            key=lambda d: d['ticker_weight'],
                            reverse=True)

    # 1b. Merge into a single df
    for ticker_data in merged_dfs:
        ticker = ticker_data['ticker']
        prices = ticker_data['prices']
        ticker_weight = ticker_data['ticker_weight']
        save_nav = False if ticker_data['save_nav'] == False else save_nav
        # If empty, just use the current prices
        if dailynav.empty:
            dailynav = prices
        else:
            dailynav = pd.merge(dailynav, prices, how='inner', on='date')

        # Process and clean daily NAV
        dailynav = dailynav.sort_index()
        # Replace NaN with prev value, if no prev value then zero
        dailynav[ticker + '_price'].fillna(method='backfill', inplace=True)
        dailynav[ticker + '_price'].fillna(method='ffill', inplace=True)
        # Include weights
        dailynav[ticker + '_initial_weight'] = ticker_weight
        # include percentage change
        dailynav[ticker + '_day_return'] = dailynav[ticker +
                                                    '_price'].pct_change()
        dailynav[ticker + '_day_return'].fillna(0, inplace=True)
        # include factor of return
        dailynav[ticker +
                 '_perc_factor'] = (dailynav[ticker + '_day_return']) + 1
        dailynav[ticker + '_perc_factor'].fillna(1, inplace=True)

    # a. create a list of all rebalancing dates
    initial_date = dailynav.index.min()
    end_date = dailynav.index.max()
    try:
        rebalance_dates = create_dates_list(initial_date, end_date, rebalance)
    except Exception as e:
        # Exception occured, default to no rebalancing
        rebalance_dates = [initial_date]
        try:
            flash(
                f"Rebalancing dates could not be created. Error: {e}. Defaulted to no rebalancing.",
                "warning")
        except Exception:
            print(
                f"Rebalancing dates could not be created. Error: {e}. Defaulted to no rebalancing."
            )

    # set initial NAV value and rebalance dates
    dailynav['port_NAV'] = 100
    dailynav['rebalance_date'] = False

    # b. Loop though rebalancing dates and fill the DF
    for rebalance_date in rebalance_dates:
        # Mark the rebalance date
        dailynav.at[rebalance_date, 'rebalance_date'] = True
        # Calculate the Quantities for this day and copy to below
        start_NAV = dailynav.at[rebalance_date, 'port_NAV']

        for ticker in ticker_list:
            # Recalculate quantity for this date
            price = dailynav.at[rebalance_date, ticker + '_price']
            weight = dailynav.at[rebalance_date, ticker + '_initial_weight']
            quant = (start_NAV / price) * weight
            # Copy quantities down to end period
            dailynav.loc[dailynav.index >= rebalance_date,
                         ticker + '_quant'] = quant
            dailynav.loc[dailynav.index >= rebalance_date, ticker +
                         '_NAV_position'] = (dailynav[ticker + '_quant'] *
                                             dailynav[ticker + '_price'])

            # With quantities for each day, calculate the
            # sum product between quant and price

        dailynav['port_NAV'] = dailynav.loc[:,
                                            dailynav.columns.str.
                                            contains('_NAV_position')].sum(
                                                axis=1)

    # Recalculate actual weights each day
    for ticker in ticker_list:
        dailynav[ticker + "_weight"] = (dailynav[ticker + '_NAV_position'] /
                                        dailynav['port_NAV'])
        # Cumulative compounded returns
        dailynav[ticker + '_cum_return'] = dailynav[ticker +
                                                    '_perc_factor'].cumprod()
        # NAV
        dailynav[ticker + '_NAV'] = dailynav[ticker + '_cum_return'] * 100
        # calculate the weighted return for this ticker
        dailynav[ticker +
                 '_weighted_chg'] = (dailynav[ticker + '_day_return'] *
                                     dailynav[ticker + '_initial_weight'])

    # Daily rebalancing is below (i.e. weights are always fixed)
    dailynav['port_day_return'] = dailynav['port_NAV'].pct_change()
    dailynav['port_perc_factor'] = (dailynav['port_day_return']) + 1
    dailynav['port_cum_return'] = dailynav['port_perc_factor'].cumprod()

    # Keep this only so loops through tickers can also find the
    # "ticker" port
    dailynav['port_initial_weight'] = 1

    # Save df to file
    if save_nav == true:
        pickle_it('save', filename, dailynav)

    # dailynav.to_clipboard(excel=True)
    return dailynav


@MWT(timeout=6000)
def correlation_matrix(df, html=False):
    """
    html = True will return an html table
    html = False will return a highcharts ready object
    """
    df = df.loc[:, df.columns.str.contains('_day_return')]
    df.columns = df.columns.str.rstrip('_day_return')
    df = df.rename(columns={'po': 'Portfolio'})
    corr_table = df.corr(method='pearson', min_periods=1)
    if html is True:
        output = corr_table.to_html(
            justify='center',
            float_format="%.4f",
            classes=['table', 'table-server', 'heatmap'])
    else:
        cols = df.columns.tolist()
        data = []
        for x_ticker in cols:
            for y_ticker in cols:
                x_ticker_pos = cols.index(x_ticker)
                y_ticker_pos = cols.index(y_ticker)
                data.append([
                    x_ticker_pos, y_ticker_pos,
                    corr_table.at[x_ticker, y_ticker] * 100
                ])

        output = {'categories': cols, 'data': data}
        # data format for highcharts is:
        # data =  [[x, y, value], ...],

    return (output)


@MWT(timeout=6000)
def rolling_correlation_matrix(df, window=30, filter=None, BTC_only=True):
    # Accepted filters = 'upside', 'downside', None
    df = df.loc[:, df.columns.str.contains('_day_return')]
    df.columns = df.columns.str.rstrip('_day_return')
    df = df.rename(columns={'po': 'Portfolio'})
    cols = df.columns.tolist()
    for x_ticker in cols:
        for y_ticker in cols:
            if BTC_only is True:
                if 'BTC' not in x_ticker and 'BTC' not in y_ticker:
                    continue
            if x_ticker != y_ticker:
                # check if the inverse exists
                checker = [
                    x for x in df.columns.tolist()
                    if y_ticker + ' and ' + x_ticker in x
                ]
                if checker == []:
                    df['Rolling Correlation between: ' + x_ticker + ' and ' +
                       y_ticker + f' ({window} days)'] = (df[x_ticker].rolling(
                           window).corr(df[y_ticker])) * 100

    series = []
    cols = df.columns.tolist()
    correl_cols = [x for x in cols if "Rolling Correlation" in x]
    for col in correl_cols:
        series_data = {
            'name': col.upper(),
            'data': df_col_to_highcharts(df, col),
            'tooltip': {
                'valueDecimals': 2
            }
        }
        series.append(series_data)
    return (series)


@MWT(timeout=6000)
# Create a list of dates for which the portfolio is rebalanced
def create_dates_list(start_date, end_date, period):
    """
    Creates a list of dates between start_date and end_date
    with a step between each date.
    """
    if period is None:
        period = 'never'
    period = period.strip('"').lower()
    step_days = 0
    step_months = 0
    if period == 'daily':
        step_days = 1
    elif period == 'weekly':
        step_days = 7
    elif period == 'monthly':
        step_months = 1
    elif period == 'quarterly':
        step_months = 3
    elif period == 'semi-annually':
        step_months = 6
    elif period == 'annually' or period == 'yearly':
        step_months = 12
    elif period == 'never':
        return [start_date]
    else:
        raise Exception(
            "Rebalancing period is invalid. Valid options are: daily, weekly, monthly, quarterly, semi-annually, annually, never"
        )

    dates = []
    dt = start_date
    while dt <= end_date:
        dates.append(dt.strftime("%Y-%m-%d"))
        if step_days > 0:
            dt += timedelta(days=step_days)
        if step_months > 0:
            dt += relativedelta(months=step_months)
    return dates


@timing
def create_sim_dict(allocation,
                    portfolio,
                    fx='USD',
                    start_date=None,
                    end_date=None,
                    rebalance=None):
    """
    This method executes the generateNAV but returns the parameters
    along with the nav
    """
    return_dict = {
        'allocation': allocation,
        'portfolio': portfolio,
        'fx': fx,
        'start_date': start_date,
        'end_date': end_date
    }
    return_dict['df'] = create_nav(portfolio=portfolio,
                                   force=False,
                                   fx=fx,
                                   start_date=start_date,
                                   end_date=end_date,
                                   btc_allocation=allocation,
                                   rebalance=rebalance)
    return return_dict


@MWT(timeout=60000)
@timing
def simulate_btc_allocations(allocations,
                             portfolio,
                             fx='USD',
                             start_date=None,
                             end_date=None,
                             rebalance=None):
    """
    allocations = list of allocations ex: [0.05, 0.10, 0.25]
    returns a list of DFs with the NAV for each allocation
    """

    if allocations is None:
        allocations = [0]

    # Include a zero allocation - i.e. no BTC
    if 0 not in allocations:
        allocations.append(0)

    allocations = sorted(allocations)

    # Function to be executed concurrently
    def create_sim_dict_thread(allocation):
        return create_sim_dict(allocation, portfolio, fx, start_date, end_date,
                               rebalance)

    # Using ThreadPoolExecutor to run threads concurrently
    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(create_sim_dict_thread, allocation): allocation
            for allocation in allocations
        }

        alloc_list = []

        for future in as_completed(futures):
            alloc_list.append(future.result())

    # Sort the results based on the original allocation order
    alloc_list.sort(key=lambda x: x['allocation'])

    return alloc_list


@MWT(timeout=6000)
def portfolio_metadata(allocations):
    # receives a list of allocations
    # returns metadata
    port_results = {}
    for allocation in allocations:
        tmp = {
            'allocation': allocation['allocation'],
            'port_pre': allocation['portfolio'],
            'fx': allocation['fx'],
            'start_date': allocation['start_date'],
            'end_date': allocation['end_date'],
        }
        tmp['port_post'] = add_btc_allocation(allocation['portfolio'],
                                              allocation['allocation'])
        df = allocation['df']
        tmp['port_results'] = simulation_metadada(df, port=True)
        port = f'portfolio_BTC@{allocation["allocation"]}'
        port_results[port] = tmp

    return port_results


@MWT(timeout=60000)
def simulation_metadada(df, port=False):
    """
    Creates a summary metadata coming from the results of a simulation
    when port is true, only analysis the portfolio return,
    otherwise will analyze all assets
    """
    tmp = {}
    cols = df.columns.values.tolist()
    price_cols = [x for x in cols if "_price" in x]
    tickers = tmp['tickers'] = [x.strip('_price') for x in price_cols]
    # Get the data for each of the tickers
    asset_results = {}
    if port is True:
        tickers = ['port']
    for ticker in tickers:
        asset_results[ticker] = get_stats(df, ticker)
    tmp['asset_results'] = asset_results
    return tmp


@MWT(timeout=60000)
def get_stats(df, ticker):
    # Gets statistics for a ticker coming from a DF
    rfr = get_risk_free_rate(df.index[0], df.index[-1])
    stats = {
        'number_points':
        df[ticker + '_day_return'].count(),
        'total_return':
        df[ticker + '_cum_return'][-1],
        'max_return':
        df[ticker + '_cum_return'].max(),
        'lowest_return':
        df[ticker + '_cum_return'].min(),
        'volatility_daily':
        df[ticker + '_day_return'].std(),
        'annualization_factor':
        annualization_factor(df),
        'volatility_annual':
        df[ticker + '_day_return'].std() * annualization_factor(df)**.5,
        'return_annual':
        ((df[ticker + '_cum_return'][-1])
         **(annualization_factor(df) / df[ticker + '_day_return'].count())) -
        1,
    }
    stats['sharpe_ratio'] = (stats['return_annual'] -
                             rfr) / stats['volatility_annual']

    if ticker == 'port':
        Y = df['port_NAV'].pct_change().dropna()
    else:
        Y = df[ticker + '_price'].pct_change().dropna()
    stats['hist_VaR_95'] = rp.RiskFunctions.VaR_Hist(Y, alpha=0.05)
    stats['max_DD_abs'] = rp.RiskFunctions.MDD_Rel(Y)
    stats['avg_DD_abs'] = rp.RiskFunctions.ADD_Rel(Y)
    stats['DaR_DD_abs'] = rp.RiskFunctions.DaR_Rel(Y, alpha=0.05)

    # Calculate the Drawdown Data for Charts
    cumulative_returns = (1 + Y).cumprod()
    peak_value = cumulative_returns.expanding().max()
    drawdown = cumulative_returns / peak_value - 1

    # Epoch for highcharts
    # drawdown.index = pd.to_datetime(drawdown.index)
    drawdown.index = (drawdown.index - datetime(1970, 1, 1)).total_seconds()
    drawdown.index = drawdown.index * 1000
    drawdown.index = drawdown.index.astype(np.int64)

    stats['dd_chart_data'] = {
        'x': drawdown.index.to_list(),
        'y': drawdown.to_list()
    }

    return stats


@MWT(timeout=6000)
def annualization_factor(df):
    """
    Receives a df and returns the number of periods to apply
    to annualize the returns. For BTC this should be close to
    365 as it trades daily. For stocks should be close to 252.
    Args:
        df (_type_): _description_
    """
    start_date = df.index[0]
    end_date = df.index[-1]
    number_of_days = (end_date - start_date).days
    fraction_of_year = number_of_days / 365
    data_points = len(df)
    annualization_factor = data_points / fraction_of_year
    return int(round(annualization_factor, 0))


@MWT(timeout=6000)
def metadata_returns(all_dfs, allocations, rebalance):

    df = all_dfs[0]
    start_date = all_dfs[0].index[0]
    end_date = all_dfs[0].index[-1]
    rfr = get_risk_free_rate(start_date, end_date)
    original_return = (df["port_cum_return"][-1] - 1)
    an_return = ((original_return + 1)**(annualization_factor(df) /
                                         df["port_cum_return"].count())) - 1
    original_vol = df["port_day_return"].std() * annualization_factor(df)**.5
    original_sharpe = (an_return - rfr) / original_vol

    return_dict = {
        'start_date': start_date,
        'end_date': end_date,
        'diff': relativedelta(end_date, start_date),
        'original_return': original_return,
        'annualized_return': an_return,
        'original_vol': original_vol,
        'original_sharpe': original_sharpe,
        'allocations': {},
        'rfr': rfr,
        'max_sharpe': (0, original_sharpe),
        'max_return': (0, original_return)
    }

    # Return of allocations
    for allocation in allocations:
        if allocation == 0:
            continue
        df = all_dfs[allocation]
        # Return comparison
        this_return = (df["port_cum_return"][-1] - 1)
        an_return = ((this_return + 1)**(annualization_factor(df) /
                                         df["port_cum_return"].count())) - 1
        tmp_dict = {'this_return': this_return}
        tmp_dict['diff_return'] = round(this_return - original_return, 2)
        tmp_dict['multiplier_return'] = round(this_return / original_return, 2)
        if this_return > original_return:
            tmp_dict['higher'] = True
        else:
            tmp_dict['higher'] = False
        return_dict['allocations'][allocation] = tmp_dict
        # Check if this is the highest return
        if tmp_dict['this_return'] > return_dict['max_return'][1]:
            return_dict['max_return'] = (allocation, tmp_dict['this_return'])

        # volatility
        this_vol = df["port_day_return"].std() * annualization_factor(df)**.5
        tmp_dict['vol'] = this_vol
        tmp_dict['multiplier_vol'] = round(this_vol / original_vol, 2)
        # Sharpe ratio
        tmp_dict['sharpe'] = (an_return - rfr) / this_vol
        # Check if this is the highest sharpe
        if tmp_dict['sharpe'] > return_dict['max_sharpe'][1]:
            return_dict['max_sharpe'] = (allocation, tmp_dict['sharpe'])

        tmp_dict['multiplier_sharpe'] = round(
            tmp_dict['sharpe'] / original_sharpe, 2)

    return (return_dict)


# Efficient Frontier and Risk Model
@MWT(timeout=6000)
def risk_parity_model(portfolio, start_date, end_date, uuid_tmp):
    error = []
    return_dict = {}
    # assets =  ['BTC-USD', 'SPY', 'QQQ', 'TLT', 'HYG', 'KBE', 'GLD',
    #            'SLV', 'GSG', 'VO', 'VEA', 'DODIX', 'VEU', 'IEV',
    #            'ACWI', 'VNQ', 'VTI']
    # start_date = '2015-01-01' ---> YYYY-MM-DD
    # end_date = '2020-12-30'
    assets = [x[0] for x in portfolio]
    # Store original weights
    return_dict['original_portfolio'] = portfolio

    # yFinance ticker for BTC is BTC-USD
    if 'BTC-USD' not in assets:
        assets.append('BTC-USD')
    if 'BTC' in assets:
        assets.remove('BTC')

    try:
        assets.sort()
        # Downloading data
        data = get_yf(assets, start_date, end_date)
        # Calculating returns
        Y = data[assets].pct_change().dropna()
    except Exception as e:
        error.append(f'Error downloading the data: {e}')
        flash(f'Error downloading the data: {e}', 'danger')

    # 2. Estimating Mean Variance Portfolios
    # 2.1 Calculating the portfolio that maximizes Sharpe ratio.
    # Building the portfolio object
    try:
        port = rp.Portfolio(returns=Y)

        # Calculating optimal portfolio
        # Select method and estimate input parameters:
        method_mu = 'hist'  # Method to estimate expected returns based on historical data.
        method_cov = 'hist'  # Method to estimate covariance matrix based on historical data.

        port.assets_stats(method_mu=method_mu, method_cov=method_cov, d=0.94)

        # Estimate optimal portfolio:
        model = 'Classic'  # Could be Classic (historical), BL (Black Litterman) or FM (Factor Model)
        rm = 'MV'  # Risk measure used, this time will be variance
        obj = 'Sharpe'  # Objective function, could be MinRisk, MaxRet, Utility or Sharpe
        hist = True  # Use historical scenarios for risk measures that depend on scenarios
        rf = 0  # Risk free rate
        l = 0  # Risk aversion factor, only useful when obj is 'Utility'
        w = port.optimization(model=model,
                              rm=rm,
                              obj=obj,
                              rf=rf,
                              l=l,
                              hist=hist)
        return_dict['risk_weights'] = w.to_dict()
    except Exception as e:
        error.append(f'Error calculating the optimal portfolio: {e}')
        flash(f'Error calculating the optimal portfolio: {e}', 'danger')
        return_dict['risk_weights'] = None

    # Efficient Frontier Calculation and chart
    # Using MV risk measure
    try:
        points = 50  # Number of points of the frontier
        frontier = port.efficient_frontier(model=model,
                                           rm=rm,
                                           points=points,
                                           rf=rf,
                                           hist=hist)
        label = 'Max Risk Adjusted Return Portfolio'  # Title of point
        mu = port.mu  # Expected returns
        cov = port.cov  # Covariance matrix
        returns = port.returns  # Returns of the assets
        import matplotlib
        matplotlib.use('Agg')
        fig, ax = plt.subplots()
        ax = rp.plot_frontier(w_frontier=frontier,
                              mu=mu,
                              cov=cov,
                              returns=returns,
                              rm=rm,
                              rf=rf,
                              alpha=0.05,
                              cmap='plasma',
                              w=w,
                              label=label,
                              marker='*',
                              s=16,
                              c='r',
                              height=6,
                              width=10,
                              ax=None)
        # Export the chart for Flask
        # Save the chart as an image in memory
        static_folder_path = os.path.join(current_app.root_path, 'static/')
        # Check if the tmp directory exists, if not create it
        try:
            tmp_folder = os.path.join(static_folder_path, 'tmp_imgs/')
            os.mkdir(tmp_folder)
            # Maintenance: delete all files older than n minutes
            delete_old_files(tmp_folder, 5)

        except Exception:
            pass

        filename = f'{uuid_tmp}_ef.png'
        plot_path = os.path.join(tmp_folder, filename)
        ax.figure.savefig(plot_path)

        # Plotting efficient frontier composition
        fig2, ax2 = plt.subplots()
        ax2 = rp.plot_frontier_area(w_frontier=frontier,
                                    cmap="tab20",
                                    height=6,
                                    width=10,
                                    ax=None)
        filename = f'{uuid_tmp}_al.png'
        plot_path = os.path.join(tmp_folder, filename)
        ax2.figure.savefig(plot_path)

        # Close the figures
        plt.close(fig)
        plt.close(fig2)

    except Exception as e:
        error.append(f'Error calculating the efficient frontier: {e}')
        flash(f'Error calculating the efficient frontier: {e}', 'danger')
        return_dict['risk_contributions'] = None

    # 2.2 Calculating the risk parity weights
    try:
        rp_w = port.rp_optimization(model='Classic',
                                    rm='MV',
                                    rf=0,
                                    b=None,
                                    hist=True)
        return_dict['rp_weights'] = rp_w.to_dict()
    except Exception as e:
        error.append(f'Error calculating the risk parity weights: {e}')
        flash(f'Error calculating the risk parity weights: {e}', 'danger')
        return_dict['rp_weights'] = None

    # 2.3 Calculating the Risk Contributions before and after
    try:
        port_rc = rp.RiskFunctions.Risk_Contribution(w,
                                                     port.cov,
                                                     returns=Y,
                                                     rm='MV')
        rp_rc = rp.RiskFunctions.Risk_Contribution(rp_w,
                                                   port.cov,
                                                   returns=Y,
                                                   rm='MV')
        return_dict['risk_contributions'] = {
            'before': list(port_rc),
            'after': list(rp_rc)
        }
    except Exception as e:
        error.append(f'Error calculating the risk contributions: {e}')
        flash(f'Error calculating the risk contributions: {e}', 'danger')
        return_dict['risk_contributions'] = None

    return_dict['error'] = error
    return return_dict


@MWT(timeout=60 * 60 * 24)
def run_optimizations(portfolio, start_date, end_date, uuid_pkl):
    status = {
        'message': 'Kicking off the optimization process...',
        'done': False,
        'error': [],
        'results': pd.DataFrame([]),
        'times': [],
        'html': '<span class="text-info loadanim">Loading...</span>',
    }

    # Save the status
    pickle_it('save', uuid_pkl, status)

    assets = [x[0] for x in portfolio]

    # yFinance ticker for BTC is BTC-USD
    if 'BTC-USD' not in assets:
        assets.append('BTC-USD')
    if 'BTC' in assets:
        assets.remove('BTC')

    try:
        assets.sort()
        # Downloading data
        data = get_yf(assets, start_date, end_date)
        # Calculating returns
        Y = data[assets].pct_change().dropna()
        port = rp.Portfolio(returns=Y)
        method_mu = 'hist'  # Method to estimate expected returns based on historical data.
        method_cov = 'hist'  # Method to estimate covariance matrix based on historical data.
        # Get stats
        port.assets_stats(method_mu=method_mu, method_cov=method_cov, d=0.94)
        model = 'Classic'  # Could be Classic (historical), BL (Black Litterman) or FM (Factor Model)
        rm = 'MV'  # Risk measure used, this time will be variance
        obj = 'Sharpe'  # Objective function, could be MinRisk, MaxRet, Utility or Sharpe
        hist = True  # Use historical scenarios for risk measures that depend on scenarios
        rf = 0  # Risk free rate
        l = 0  # Risk aversion factor, only useful when obj is 'Utility'
    except Exception as e:
        status['error'].append(
            f'Error downloading the data or calculating returns: {e}')
        status['message'] == 'Errors found. Could not complete optimization.'
        status['done'] = True
        pickle_it('save', uuid_pkl, status)

    # Kick off the optimizations
    status['rms'] = rms = [
        'MV', 'MAD', 'MSV', 'FLPM', 'SLPM', 'CVaR', 'CDaR', 'UCI'
    ]

    # Optimization of single risk measure
    def optimize_portfolio_single_rm(port, model, rm, obj, rf, l, hist, index,
                                     uuid_pkl, status):
        # kick off timer
        start = time()

        status[
            'message'] += f'<br>Starting thread. Optimizing for {rm}... {index + 1} / {str(len(rms))}'
        pickle_it('save', uuid_pkl, status)
        w = port.optimization(model=model,
                              rm=rm,
                              obj=obj,
                              rf=rf,
                              l=l,
                              hist=hist)
        # stop timer and calculate time
        time_it = time() - start

        status[
            'message'] = f'Done with thread: {rm}. Took {round(time_it,2)}s to complete.'
        w.columns = [rm]
        w.style.format("{:.2%}").background_gradient(cmap='YlGn')
        status['results'] = pd.concat([status['results'], w], axis=1)
        status['times'].append((rm, time_it))
        status['html'] = status['results'].style.format(
            "{:.2%}").background_gradient(cmap='YlGn').to_html()
        pickle_it('save', uuid_pkl, status)
        return status

    try:
        for i, rm in enumerate(rms):
            status = optimize_portfolio_single_rm(port, model, rm, obj, rf, l,
                                                  hist, i, uuid_pkl, status)

    except Exception as e:
        status['error'].append(f'Error running optimization: {e}')
        status['message'] == 'Errors found. Could not complete optimization.'
        status['done'] = True
        pickle_it('save', uuid_pkl, status)

    # Seems like everything went fine. Send final message
    status['message'] = 'Optimization Complete'
    status['done'] = True
    pickle_it('save', uuid_pkl, status)


# ---------------------------------
# CHARTS --------------------------
# ---------------------------------


@MWT(timeout=6000)
def pie_chart(portfolio, tickers):
    """
    Returns a formatted pie chart for the portfolio.
    """
    pie_data = []
    for line in portfolio:
        if line[0] == '':
            continue
        tmp_dict = {}
        tmp_dict['y'] = round(line[1] * 100, 2)
        tmp_dict['name'] = (ticker_to_name(line[0], tickers) + " (" + line[0] +
                            ")")
        pie_data.append(tmp_dict)
    return pie_data


@MWT(timeout=6000)
def stats_charts(data, filter='portfolios', rfr=0):
    # filter = assets or portfolios
    datasets = []
    mapping = {
        'return_annual': {
            'name':
            "Return<br><span style='font-size: 10px; font-style: italic;'>annualized</span>",
            'multiplier': 100,
        },
        'volatility_annual': {
            'name':
            "Volatility<br><span style='font-size: 10px; font-style: italic;'>annualized</span>",
            'multiplier': 100,
        },
        'sharpe_ratio': {
            'name':
            f"Sharpe Ratio<br><span style='font-size: 10px; font-style: italic;'>risk free rate = {jformat(rfr*100,2)}%</span>",
            'multiplier': 1,
        }
    }
    chart_items = ['return_annual', 'volatility_annual', 'sharpe_ratio']
    categories = []
    # create empty datasets for storage
    for item in chart_items:
        datasets.append({'name': item, 'data': []})
    if filter.lower() == 'portfolios':
        for key, value in data['PORTFOLIOS'].items():
            if value['allocation'] == 0:
                alloc_name = "original portfolio"
            else:
                alloc_name = '(+) ' + jformat(value['allocation'] * 100,
                                              2) + '% BTC'
            # save x axis label
            categories.append(alloc_name)
            # save data for each chart item
            for k, v in value['port_results']['asset_results']['port'].items():
                if k in chart_items:
                    for ds in datasets:
                        if ds['name'] == k:
                            ds['data'].append(v * mapping[k]['multiplier'])

    elif filter.lower() == 'assets':
        for key, value in data['ASSETS']['asset_results'].items():
            categories.append(key)
            # save data for each chart item
            for k, v in value.items():
                if k in chart_items:
                    for ds in datasets:
                        if ds['name'] == k:
                            ds['data'].append(v * mapping[k]['multiplier'])

    # rename dataset names
    for item in datasets:
        item['name'] = mapping[item['name']]['name']

    return {'categories': categories, 'datasets': datasets}


@MWT(timeout=6000)
def price_charts(df):
    # filter = assets or portfolios
    cols = df.columns
    price_cols = [x for x in cols if "_price" in x]
    series = []
    for col in price_cols:
        series_data = {
            'name': col.strip('_price').upper(),
            'data': df_col_to_highcharts(df, col),
            'tooltip': {
                'valueDecimals': 2
            }
        }
        series.append(series_data)

    return series


@MWT(timeout=6000)
def portfolios_charts(allocations):
    # receives a list of allocations
    # returns metadata
    series = []
    for allocation in allocations:
        df = allocation['df']
        if allocation['allocation'] == 0:
            series_name = "Original Portfolio"
        else:
            series_name = "(+) " + str(
                jformat(allocation['allocation'] * 100,
                        2)) + '% BTC Allocation'
        series_data = {
            'name': series_name,
            'data': df_col_to_highcharts(df, 'port_NAV'),
            'tooltip': {
                'valueDecimals': 2
            }
        }
        series.append(series_data)

    return series


@MWT(timeout=6000)
def scatter_charts(allocations):
    allocations = sorted(allocations, key=lambda d: d['allocation'])
    # Filter for original portfolio
    port_series = []
    # Get original DF i.e. zero allocation to BTC
    for allocation in allocations:
        if allocation['allocation'] == 0:
            df = allocation['df'].copy()
            df4 = allocation['df'].copy()
            df4.rename(columns={'port_day_return': 'original_day_return'},
                       inplace=True)
    counter = 0
    for allocation in allocations:
        if allocation['allocation'] != 0:
            df3 = pd.merge(df4, allocation['df'], how='left', on='date')
            df3 = df3.set_index('original_day_return')
            df3 = df3['port_day_return'].copy()
            if isinstance(df3, pd.Series):
                df3 = df3.to_frame()
            data = df3.to_records(index=True).tolist()
            data = [list(elem) for elem in data]
            series_data = {
                'name': "(+) " + str(allocation['allocation'] * 100) +
                '% BTC vs. Original Portfolio',
                'data': data,
                'visible': True if counter == 0 else False,
            }
            counter += 1
            port_series.append(series_data)

    series = []
    df2 = df.set_index('port_day_return')
    cols = df2.columns
    price_cols = [x for x in cols if "_day_return" in x]

    for col in price_cols:
        data = df2[col].copy()
        if isinstance(data, pd.Series):
            data = data.to_frame()
        data = data.to_records(index=True).tolist()
        data = [list(elem) for elem in data]
        series_data = {
            'name':
            col.strip('_day_return').upper() + ' vs. Original Portfolio',
            'data': data,
            'visible': True if 'BTC' in col else False,
        }
        series.append(series_data)

    results = {'assets': series, 'portfolios': port_series}

    return results


@MWT(timeout=6000)
def allocation_chart(df, ticker_list):
    chart_data_list = []
    #  Looping through Tickers
    for ticker in ticker_list:
        tmp_dict = {}
        if ticker == 'BTC':
            tmp_dict['color'] = '#fd7e14'
        tmp_dict['name'] = ticker
        tmp_dict['type'] = 'area'
        tmp_dict['turboThreshold'] = 0
        tmp_dict['data'] = df_col_to_highcharts(df, ticker + "_weight")
        chart_data_list.append(tmp_dict)

    return chart_data_list


@MWT(timeout=6000)
def annual_return_table(df, ticker_list, agg='year'):
    """
    Takes df, ticker_list
    Creates an annual table with ranked returns to each ticker
    . Keep tickers in same color to better visualize
    . Show return that year inside table cell
    . create an html table for display
    Args:
        df (_type_): _description_
        ticker_list (_type_): _description_
    """

    # Gets the last and first days in each month, year
    if agg == 'month':
        df['dates'] = df.index
        # Group by month and year
        resultDf = df.groupby([df.index.year,
                               df.index.month]).agg(["first", "last"])
        for ticker in ticker_list:
            # include ticker performance in period
            resultDf[ticker +
                     "_month"] = ((resultDf[(ticker + "_price", "last")] -
                                   resultDf[(ticker + "_price", "first")]) /
                                  resultDf[(ticker + "_price", "first")])

    if agg == 'year':
        df['dates'] = df.index
        # Group by year
        resultDf = df.groupby([df.index.year]).agg(["first", "last"])
        # include ticker performance in period
        for ticker in ticker_list:
            resultDf[ticker +
                     "_year"] = ((resultDf[(ticker + "_price", "last")] -
                                  resultDf[(ticker + "_price", "first")]) /
                                 resultDf[(ticker + "_price", "first")])

    # Create the table
    # monthly return tables need to be transposed compared to year tables
    # Create annual table
    return_table = []
    for __, row in resultDf.iterrows():
        tmp = {
            'start_date': row[('dates', 'first')],
            'end_date': row[('dates', 'last')],
        }
        for ticker in ticker_list:
            # Store performance at dictionary
            tmp[ticker + '_performance'] = float(row[ticker + '_' + agg])

        return_table.append(tmp)

    # Create ranking table
    for element in return_table:
        items = []
        rnk = []
        for ticker in ticker_list:
            rnk.append(element[ticker + '_performance'])
            items.append((float(element[ticker + '_performance']), ticker))
        element['ranking'] = sorted(items, reverse=True)
    return return_table


@MWT(timeout=6000)
def color_map(ticker_list):
    # Create unique color map by ticker
    # General pallete of colors
    colors = [
        '#5DADE2', '#F1C40F', '#58D68D', '#F7DC6F', '#73C6B6', '#F4D03F',
        '#45B39D', '#F7DC6F', '#16A085', '#F0E68C', '#117A65'
    ]
    color_map = {}
    counter = 0
    for ticker in ticker_list:
        if ticker == 'BTC':
            color_map[ticker] = '#F9A136'
        else:
            color_map[ticker] = colors[counter]
        counter += 1
        if counter > (len(colors) - 1):
            counter = 0
    return color_map


def report_qs(ticker):
    import dependencies.quantstats as qs
    qs.extend_pandas()
    df = historical_prices(ticker)
    df = df['close_converted'].pct_change().dropna()
    html = qs.reports.html(df, 'aapl', title='Comparison ')
    return (html)


def get_qs_stats(ticker, benchmark='BTC'):
    import dependencies.quantstats as qs
    qs.extend_pandas()
    df = historical_prices(ticker)
    df = df['close_converted'].pct_change().dropna()
    stats = qs.reports.metrics(df, ticker=ticker, benchmark=benchmark)

    # Load Glossary
    filename = os.path.join(basedir, 'static/json_files/quant_glossary.json')
    with open(filename, 'r') as handle:
        glossary = json.load(handle)

    # Create a reverse mapping dictionary for easy lookup
    index_to_key = {value['index']: key for key, value in glossary.items()}

    # Add new columns with key, short_description, long_description, format, and decimal_places
    stats['key'] = stats.index.map(lambda index: index_to_key.get(index))
    stats['short_description'] = stats['key'].map(lambda key: glossary.get(
        key, {'short_description': None})['short_description'])
    stats['long_description'] = stats['key'].map(lambda key: glossary.get(
        key, {'long_description': None})['long_description'])
    stats['format'] = stats['key'].map(
        lambda key: glossary.get(key, {'format': None})['format'])
    stats['decimal_places'] = stats['key'].map(lambda key: glossary.get(
        key, {'decimal_places': None})['decimal_places'])

    # Categorize the dataframe
    filename = os.path.join(basedir, 'static/json_files/quant_categories.json')
    with open(filename, 'r') as handle:
        categories = json.load(handle)

    # Add category column based on the key
    def get_category(key):
        for category, metrics in categories.items():
            if key in metrics:
                return category
        return 'other_metrics'

    stats['category'] = stats['key'].apply(get_category)

    return stats
