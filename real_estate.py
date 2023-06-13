import os
import pgeocode
import json
import uuid
from datetime import datetime
import numpy as np
import numpy_financial as npf
import pandas as pd
from scipy import stats
from backend.config import basedir
from backend.portfolio_analytics import portfolio_analysis, annualization_factor
from backend.utils import pickle_it, file_created_today, average_dfs
from backend.config import basedir, home_dir
from pricing_engine.engine import historical_prices, get_risk_free_rate, realtime_price
import base64
from io import BytesIO
from matplotlib.figure import Figure
import seaborn as sns
from matplotlib.ticker import FuncFormatter
from matplotlib.patches import Rectangle
from backend.ansi_management import jformat
from backend.decorators import MWT


# Returns a list of all Case-Schiller indices and composites
def load_indices():
    filename = os.path.join(basedir, 'static/json_files/case-schiller.json')
    with open(filename, 'r') as handle:
        data = json.load(handle)
    return (data)


# Finds the closest index to a specific zip code (string)
# Sample results:
# 33131 input:
# ({'ticker': 'MIXR',
# 'name': 'South Florida metropolitan area',
# 'description': 'Miami–Fort Lauderdale–Pompano Beach, FL', 'zip': '33101'},
# 1.9838516471514251)
# Empty Result:
# (None, 99999999999999)
def find_closest(zipcode):
    # Returns None and 999999 if no match
    dist = pgeocode.GeoDistance('us')
    indices = load_indices()
    closest = None
    distance = 99999999999999
    for index in indices:
        check = dist.query_postal_code(zipcode, index['zip'])
        if np.isnan(check):
            continue
        if check < distance:
            distance = check
            closest = index
    if closest is None:
        return_dict = {
            "ticker": "SPCS20RSA",
            "name": "Composite 20 Index",
            "description":
            "A composite index of the home price index for 20 major Metropolitan Statistical Areas in the United States.",
            "zip": None,
            "property_tax": 0.01,
        }
        return (return_dict, 99999999999999)
    return (closest, distance)


# Gets statistics on a specific index
def get_stats_cs(no_btc=True):

    if no_btc is True:
        # Try to load the data if still new
        filename = os.path.join(home_dir, 'case_shiller_stats_nobtc.pkl')
    else:
        filename = os.path.join(home_dir, 'case_shiller_stats_withbtc.pkl')

    if file_created_today(filename, hours=6):
        return (pickle_it('load', filename))

    # Create a portfolio with all the indices
    indices = load_indices()
    weights = (len(indices) + 1) / 100  # Equal weight

    portfolio = [("FRED:" + index['ticker'], weights) for index in indices]
    portfolio.append(('FRED:CPIAUCSL', weights))  # Add inflation

    tickers = [["FRED:" + index['ticker'], index['name']] for index in indices]
    tickers.append(['FRED:CPIAUCSL',
                    'Consumer Price Index (urban)'])  # Add inflation

    result = portfolio_analysis(portfolio,
                                tickers,
                                allocations=[0],
                                no_btc=no_btc)
    # Save it for later
    pickle_it('save', filename, result)
    return (result)


# Outline for the real estate class
class RealEstate:

    def __init__(self):
        self.uuid = str(uuid.uuid4())
        self.n_sims = 100
        # The start and end date of the backtesting analysis
        self.start_date = None
        self.end_date = None
        self.property_value = 500000
        self.down_payment = 0.2  # 20% downpayment
        self.expected_holding_period = 10
        self.mortgage_rate = self.get_mortage_rate()
        self.mortgage_term = 30
        self.include_deduction_as_cf = True  # Include mortgage interest deduction as "virtual" cash flow
        self.property_tax = 0.01  # As percentage of property value per year
        self.HOA_fees_month = 100
        self.repairs_month = 0
        self.major_repair = 0.02  # x% of property value
        self.major_repair_probability = 0.20  # Per year (new roof, flooded bathroom, new furnace, etc..)
        # 0.25 = 25% chance per year = once every 4 years
        self.major_repair_hours = 10
        self.maintenance_year = 0.005  # as percentage of property value
        self.buying_close_costs = 0.03
        self.closing_costs_in_loan = True
        self.selling_close_costs = 0.06
        self.marginal_tax_rate = 0.25
        self.filling_status = 'single'
        self.capital_gains_tax_rate = 0.15
        self.inflation_index = 'FRED:CPIAUCSL'
        self.mortgage_index = 'FRED:MORTGAGE30US'
        self.vacancy_rate_index = 'FRED:RRVRUSQ156N'  #  Rental Vacancy Rate in the United States (RRVRUSQ156N)
        self.zipcode = None
        self.distance_to_index = None
        self.personal_hours_week = [0, 2]
        self.personal_hourly_rate = 500
        self.government_seizure_prob = 0.01
        self.home_type = 'Buy as Primary Home'  # 'Buy as Primary Home', 'Buy to Rent', 'Rent'
        self.rent_equivalent = 2000  # Rent equivalent
        self.rent_appreciation = 0.02  # Rent appreciation per year
        self.security_deposit = 3  # Months of rent
        self.occupancy_rate = 0.90
        self.home_owners_insurance_month = 100  # Home owners insurance per month in USD
        self.insurance_deductible = 2500
        self.renters_insurance = 0.005
        self.renters_insurance_deductible = 250
        self.renovation_cost = 0.08  # Renovation cost as a percentage of property value
        self.renovation_frequency = 15
        # opportunity cost / benchmark
        self.opp_cost_benchmark = 'BTC'
        # Make future returns more conservative
        # 0.80 = 80% of past returns
        self.benchmark_adjustment = 0.5

    def get_mortage_rate(self):
        # Get the mortgage rate
        try:
            ticker = self.mortgage_index
        except AttributeError:
            ticker = 'FRED:MORTGAGE30US'
        latest_rate = historical_prices(ticker).iloc[-1]['close'] / 100
        return (latest_rate)

    def get_cs_index(self):
        # If no zipcode, return the national index
        if self.zipcode is None:
            finder = 'SPCS20RSA'
            for item in load_indices():
                if item['ticker'] == finder:
                    return (item)
        idx, self.distance_to_index = find_closest(self.zipcode)
        return (idx)

    # Case Shiller DF -- past data
    def cs_df(self):
        ticker = self.get_cs_index()['ticker']
        # Make sure index starts with source FRED
        if 'FRED' not in ticker:
            ticker = 'FRED:' + ticker
        df = historical_prices(ticker, self.start_date, self.end_date)
        df['normalized'] = df['close'] / df['close'][0] * 100
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        df = df.loc[df['log_returns'] != 0]
        return (df)

    # CPI and other DFs -- past data
    def other_dfs(self):
        # First CPI DF
        ticker = self.inflation_index
        # Make sure index starts with source FRED
        if 'FRED' not in ticker:
            ticker = 'FRED:' + ticker
        df = historical_prices(ticker, self.start_date, self.end_date)
        df['normalized'] = df['close'] / df['close'][0] * 100
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        df = df.loc[df['log_returns'] != 0]

        # Get Rental Vacancy now
        ticker = self.vacancy_rate_index
        # Make sure index starts with source FRED
        if 'FRED' not in ticker:
            ticker = 'FRED:' + ticker
        rental_vacancy_df = historical_prices(ticker, self.start_date,
                                              self.end_date)
        rental_vacancy_df['vacancy_rates'] = (rental_vacancy_df['close'] / 100)

        # BENCHMARK
        ticker = self.opp_cost_benchmark
        if ticker is None:
            ticker = 'BTC'
        b_df = historical_prices(ticker, self.start_date, self.end_date)
        b_df = b_df.resample('M').last()
        b_df['normalized'] = b_df['close'] / b_df['close'][0] * 100
        b_df['log_returns'] = np.log(b_df['close'] / b_df['close'].shift(1))
        b_df = b_df.loc[b_df['log_returns'] != 0]

        return ({
            'cpi_df': df,
            'rental_vacancy_df': rental_vacancy_df,
            'benchmark_df': b_df
        })

    def cs_stats(self):
        # Case Shiller stats
        df = self.cs_df()
        # Risk Free for the cs_df
        rfr = get_risk_free_rate(df.index[0], df.index[-1])
        df['normalized'] = df['close'] / df['close'][0]
        total_return = (df['close'][-1] / df['close'][0]) - 1
        original_return = (df["normalized"][-1] - 1)
        annualized_return = ((original_return + 1)**(
            annualization_factor(df) / df["normalized"].count())) - 1
        vol = df['normalized'].pct_change().std() * annualization_factor(
            df)**.5
        return {
            'start_date': df.index[0],
            'end_date': df.index[-1],
            'years': df.index[-1].year - df.index[0].year,
            'index': self.get_cs_index()['name'],
            'ticker': self.get_cs_index()['ticker'],
            'rfr': rfr,
            'total_return': total_return,
            'annualized_return': annualized_return,
            'annualized_vol': vol,
            'sharpe_ratio': (annualized_return - rfr) / vol,
        }

    @MWT(timeout=60 * 60 * 12)
    def run_simulation(self, dist_name='genhyperbolic'):
        # Let's start by simulating house prices
        # using the Case-Shiller index
        df_list = []
        n_periods = self.expected_holding_period * 12

        # Home Price DF
        df = self.cs_df()
        returns = df['log_returns'].dropna()

        other_dfs = self.other_dfs()

        # CPI DF
        cpi_df = other_dfs['cpi_df']
        cpi_returns = cpi_df['log_returns'].dropna()

        # Rental Vacancy DF
        rental_vacancy_df = other_dfs['rental_vacancy_df']
        rental_vacancy_returns = rental_vacancy_df['vacancy_rates'].dropna()

        # Benchmark DF
        benchmark_df = other_dfs['benchmark_df']
        # Make conservative adjustments
        benchmark_df['log_returns'] = (benchmark_df['log_returns'] *
                                       self.benchmark_adjustment)
        benchmark_df_returns = benchmark_df['log_returns'].dropna()
        spot_price = realtime_price(self.opp_cost_benchmark)['price']

        # --------------------------------------------
        # Generate Random Numbers & Simulation outputs
        # --------------------------------------------
        # Random seed for reproducibility
        seed = 8734283

        # Simulations for CPI
        dist = getattr(stats, dist_name)
        params = dist.fit(cpi_returns)
        cpi_sim_returns = dist.rvs(*params,
                                   size=(self.n_sims, n_periods),
                                   random_state=seed)

        # Simulations for benchmark
        dist = getattr(stats, dist_name)
        params = dist.fit(benchmark_df_returns)
        benchmark_sim_returns = dist.rvs(*params,
                                         size=(self.n_sims, n_periods),
                                         random_state=seed)

        # Simulations for Rental Vacancy
        dist = getattr(stats, dist_name)
        params = dist.fit(rental_vacancy_returns)
        vacancy_sim_returns = dist.rvs(*params,
                                       size=(self.n_sims, n_periods),
                                       random_state=seed)

        # Running of all simulations for Real Estate Returns
        dist = getattr(stats, dist_name)
        params = dist.fit(returns)
        sim_returns = dist.rvs(*params,
                               size=(self.n_sims, n_periods),
                               random_state=seed)

        # Major Repair needed?
        # Discrete distribution with probability self.major_repair_probability per year
        monthly_probability = 1 - (1 - self.major_repair_probability)**(1 / 12)
        # Generate n_sims * n_periods samples
        repair_samples = stats.bernoulli.rvs(monthly_probability,
                                             size=(self.n_sims, n_periods),
                                             random_state=seed)
        # Distribution of hourly work
        hour_work_samples = stats.uniform.rvs(self.personal_hours_week[0] * 4,
                                              self.personal_hours_week[1] * 4,
                                              size=(self.n_sims, n_periods),
                                              random_state=seed)
        # Assets seized? Game over
        monthly_probability = 1 - (1 - self.government_seizure_prob)**(1 / 12)
        seized_samples = stats.bernoulli.rvs(monthly_probability,
                                             size=(self.n_sims, n_periods),
                                             random_state=seed)

        # Renovation Happening?
        # Discrete distribution with probability (1 / self.renovation_frequency) per year
        monthly_probability = 1 - (1 -
                                   (1 / self.renovation_frequency))**(1 / 12)
        # Generate n_sims * n_periods samples
        renovation_samples = stats.bernoulli.rvs(monthly_probability,
                                                 size=(self.n_sims, n_periods),
                                                 random_state=seed)

        # --------------------------------------------
        # Generate Dataframe for each simulation
        # --------------------------------------------

        for sims in range(self.n_sims):
            tmp_df = pd.DataFrame(sim_returns[sims])
            tmp_df.columns = ['log_returns']
            # Include a date column
            tmp_df['date'] = pd.date_range(
                start=datetime.today(),
                periods=self.expected_holding_period * 12,
                freq='M').normalize()

            tmp_df['cum_log_returns'] = tmp_df['log_returns'].cumsum()
            tmp_df['prices'] = self.property_value * tmp_df[
                'cum_log_returns'].apply(lambda x: np.exp(x))
            tmp_df['major_repair'] = repair_samples[sims]
            tmp_df['hour_work'] = hour_work_samples[sims]
            tmp_df['seized'] = seized_samples[sims]
            tmp_df['cpi_log_returns'] = cpi_sim_returns[sims]
            tmp_df['cpi_cum_log_returns'] = tmp_df['cpi_log_returns'].cumsum()
            tmp_df['benchmark_log_returns'] = benchmark_sim_returns[sims]
            tmp_df['benchmark_cum_log_returns'] = tmp_df[
                'benchmark_log_returns'].cumsum()
            tmp_df['benchmark_prices'] = spot_price * tmp_df[
                'benchmark_cum_log_returns'].apply(lambda x: np.exp(x))
            tmp_df['rental_vacancy'] = vacancy_sim_returns[sims]
            tmp_df['renovation'] = renovation_samples[
                sims] * self.renovation_cost * self.property_value
            df_list.append(tmp_df)

        return (df_list)

    def upfront_cf(self):
        return_dict = {}
        # --------------------------------------
        #                 BUY
        # --------------------------------------
        # Create a cash flow for buying a house
        # Upfront costs & cashflow
        # Start with the downpayment
        downpayment = -self.property_value * self.down_payment
        # Closing costs
        closing_costs = (-self.property_value -
                         downpayment) * self.buying_close_costs
        # Mortgage amount
        mortgage_amount = self.property_value + downpayment
        # Check if closing costs are in loan or upfront
        if self.closing_costs_in_loan:
            mortgage_amount += -closing_costs
            closing_costs = 0
        # How many hours will you spend on this? Reviewing contracts, etc.
        PERSONAL_HOURS = 5
        return_dict['BUY_HOME'] = {
            'downpayment':
            downpayment,
            'security_deposit':
            0,
            'closing_costs':
            -self.property_value * self.buying_close_costs,
            'closing_costs_in_loan':
            self.closing_costs_in_loan,
            'closing_costs_buy':
            (-self.property_value - downpayment) * self.buying_close_costs,
            'CF_closing_costs':
            -closing_costs,
            'mortgage_amount':
            -mortgage_amount,
            'closing_personal_hours':
            PERSONAL_HOURS,
            'closing_personal_hour_cost':
            (-self.personal_hourly_rate * PERSONAL_HOURS),
        }
        # --------------------------------------
        #                 RENT
        # --------------------------------------
        PERSONAL_HOURS_RENT = 2
        return_dict['RENT_HOME'] = {
            'downpayment': 0,
            'security_deposit': -self.rent_equivalent * self.security_deposit,
            'closing_costs': 0,
            'closing_costs_in_loan': None,
            'CF_closing_costs': 0,
            'mortgage_amount': 0,
            'personal_hours': PERSONAL_HOURS_RENT,
            'personal_hour_cost':
            -self.personal_hourly_rate * PERSONAL_HOURS_RENT,
        }

        return (return_dict)

    def mortgage_details(self):
        upfront = self.upfront_cf()
        mortgage_amount = upfront['BUY_HOME']['mortgage_amount']
        monthly_pmt = -npf.pmt(self.mortgage_rate / 12,
                               self.mortgage_term * 12, mortgage_amount)
        # Let's create a dataframe with Interest and Principal
        df = pd.DataFrame()
        df['date'] = pd.date_range(start=datetime.today(),
                                   periods=self.expected_holding_period * 12,
                                   freq='M').normalize()
        df['interest'] = npf.ipmt(self.mortgage_rate / 12, df.index + 1,
                                  12 * self.mortgage_term, mortgage_amount)
        df['principal'] = npf.ppmt(self.mortgage_rate / 12, df.index + 1,
                                   12 * self.mortgage_term, mortgage_amount)
        df['pmt'] = df['interest'] + df['principal']
        df['interest_deduction'] = df['interest'] * self.marginal_tax_rate

        return_dict = {
            'mortgage_amount': mortgage_amount,
            'monthly_pmt': monthly_pmt,
            'df': df
        }
        return (return_dict)

    def cf(self):
        # All Cash Flows for Buying a house
        # --------------------------------------

        # Create Empty Dataframe
        df = pd.DataFrame()
        df['date'] = pd.date_range(start=datetime.today(),
                                   periods=self.expected_holding_period * 12,
                                   freq='M').normalize()

        # UPFRONT AMOUNTS
        upfront = self.upfront_cf()['BUY_HOME']
        # Create a blank dataframe with monthly dates
        # Now include all items in the upfront cash flow at TODAY's line
        for key, value in upfront.items():
            df[key] = 0
            df.at[0, key] = value

        # Recurring Amounts that are not simulated

        # Mortgage Payment
        # Merge with mortgage details df
        mtg_df = self.mortgage_details()['df']
        df = df.merge(mtg_df, on='date', how='left')
        # Principal balance
        df['cum_principal'] = df['principal'].cumsum()

        # HOA_fees_month
        df['HOA_fees_month'] = -self.HOA_fees_month
        df.at[0, 'HOA_fees_month'] = 0

        # Repairs / Month
        df['repairs_month'] = -self.repairs_month
        df.at[0, 'repairs_month'] = 0

        # Maintenance / Month
        df['maintenance_month'] = self.maintenance_year * self.property_value / 12
        df.at[0, 'maintenance_month'] = 0

        # Rent or Rent Equivalent adjusted by increases
        # Create a process so rent increases every 12 months
        rent = self.rent_equivalent
        df['rent_or_rent_equivalent'] = 0

        # Let's also include property tax in this loop
        property_tax = -self.property_value * self.property_tax
        df['property_tax'] = 0

        for i in range(1, self.mortgage_term * 12):
            # if multiple of 12, increase
            if i % 12 == 0:
                rent *= (1 + self.rent_appreciation)
                # Once a year payment on property tax
                df.at[i, 'property_tax'] = property_tax
            df.at[i, 'rent_or_rent_equivalent'] = rent

        # Home Owners Insurance in USD
        df['home_insurance'] = -self.home_owners_insurance_month

        # Merge with the simulations - up until now, we only needed one
        # dataframe as it is the same now for all simulations. From this
        # point on, there variables will depend on the simulations
        df_sim_list = self.run_simulation()

        updated_df_sim_list = []
        for df_sim in df_sim_list:
            # Merge / Update
            tmp_df = df_sim.merge(df, on='date', how='left')

            # Now INCLUDE THE FINAL AMOUNTS - SELLING, TAXES, ETC.
            # 1. Major Repairs = column has 0 or 1 (1 = major repair)
            # Also included in major repair is the time it takes to do it
            tmp_df['major_repair_cost'] = (tmp_df['major_repair'] * (
                (self.major_repair * self.property_value) +
                (self.major_repair_hours * self.personal_hourly_rate)))
            # 2. working hours at personal hourly rate
            tmp_df['personal_hour_cost'] = (tmp_df['hour_work'] *
                                            self.personal_hourly_rate)
            # 3. Selling costs
            # Closing costs
            tmp_df[
                'closing_costs'] = tmp_df['prices'] * self.selling_close_costs
            # Taxes due
            tmp_df['taxes_due'] = (
                (tmp_df['prices'] - self.property_value) *
                self.capital_gains_tax_rate).apply(lambda x: max(x, 0))
            # Principal outstanding
            initial_mtg = -tmp_df['mortgage_amount'].iloc[0]
            tmp_df['cum_principal'] = tmp_df['principal'].cumsum()
            tmp_df['principal_balance'] = (initial_mtg -
                                           tmp_df['cum_principal'])

            # Liquidation Value -- Payoff mortgage, closing costs, taxes due
            tmp_df['liquidation_value'] = (tmp_df['prices'] -
                                           tmp_df['principal_balance'] -
                                           tmp_df['closing_costs'] -
                                           tmp_df['taxes_due'])

            # CASH FLOW CALCULATION
            # Now let's clearly mark and assign the right signal
            # to the cash flow columns (negative or positive)
            tmp_df['CF_upfront'] = tmp_df['downpayment'] + tmp_df[
                'CF_closing_costs']
            tmp_df['CF_monthly'] = (-tmp_df['major_repair_cost'] -
                                    tmp_df['renovation'] +
                                    tmp_df['HOA_fees_month'] - tmp_df['pmt'] -
                                    tmp_df['repairs_month'] -
                                    tmp_df['maintenance_month'] +
                                    tmp_df['property_tax'] +
                                    tmp_df['home_insurance'])
            tmp_df['CF_total'] = (tmp_df['CF_upfront'] + tmp_df['CF_monthly'])
            tmp_df['CF_cum'] = tmp_df['CF_total'].cumsum()
            # PnL without considering monthly costs
            tmp_df['PnL_nocost'] = tmp_df['liquidation_value'] - tmp_df[
                'CF_upfront'].abs().iloc[0]
            tmp_df['PnL'] = tmp_df['liquidation_value'] + tmp_df['CF_cum']
            # Not real cash flows
            tmp_df['opportunity_cost'] = (-tmp_df['personal_hour_cost'] +
                                          tmp_df['interest_deduction'] -
                                          tmp_df['rent_or_rent_equivalent'])

            # END ------
            # Append this df to the list
            updated_df_sim_list.append(tmp_df)

        return (updated_df_sim_list)

    def plot_prices(self, figsize=(8, 6)):
        stats = {}
        fig = Figure(figsize=figsize)
        ax = fig.subplots()

        # Set background color transparent
        fig.patch.set_facecolor('none')

        # All text and borders in white
        ax.title.set_color('white')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        ax.yaxis.label.set_color('white')
        ax.xaxis.label.set_color('white')

        # Labels
        ax.set_xlabel("Months")
        ax.set_ylabel("Price")

        # Horizontal gridlines
        ax.grid(axis='y', color='white', linestyle='dashed', alpha=0.2)
        ax.set_axisbelow(True)  # Set gridlines behind other graph elements

        # Format x-axis labels as integer
        formatter = FuncFormatter(lambda x, pos: f'{int(x):,}')
        ax.xaxis.set_major_formatter(formatter)

        # Format y-axis labels with commas for thousands
        formatter = FuncFormatter(lambda x, pos: f'{int(x):,}')
        ax.yaxis.set_major_formatter(formatter)

        sim_prices = self.run_simulation()

        avg_path = []
        max_price = 0
        min_price = self.property_value * 100
        for i in range(self.n_sims):
            ax.plot(sim_prices[i]['prices'], color='#2472C8', alpha=0.1)
            max_price = max(max_price, sim_prices[i].iloc[-1]['prices'])
            min_price = min(min_price, sim_prices[i].iloc[-1]['prices'])
        for i in range(self.expected_holding_period * 12):
            prices = []
            for k in range(self.n_sims):
                prices.append(sim_prices[k].iloc[i]['prices'])
            avg_path.append(np.mean(prices))

        stats['max_price'] = max_price
        stats['min_price'] = min_price
        stats['avg_final_price'] = avg_path[-1]

        # Add the average simulation path
        start_price = self.property_value
        ax.plot(avg_path, linewidth=4, color='#fd7e14', label='average')

        ax.set_title(
            f'Monte Carlo Home Price Forecasts\n{jformat(self.expected_holding_period * 12, 0)} months forecasted, {jformat(self.n_sims, 0)} simulations',
            color='white')

        # Add arrow annotation for the final average price
        final_price_avg = avg_path[-1]
        ax.annotate(
            f'Final average forecast: ${final_price_avg:,.0f}',
            color='#5fba7d',
            xy=((self.expected_holding_period * 12) - 1,
                (final_price_avg * 1.03)),
            xytext=(int(self.expected_holding_period * 12 * 0.3),
                    final_price_avg * 1.1),
            arrowprops=dict(facecolor='green',
                            arrowstyle="->",
                            color='white',
                            lw=2),
            fontsize=14,
            bbox=dict(facecolor='black', alpha=0.5),
        )

        # Auto-scale the y-axis to show 90% of the final prices
        ax.set_ylim([start_price * 0.95, max_price])

        # Save it to a temporary buffer.
        buf = BytesIO()
        fig.savefig(buf, format="png", transparent=True)

        # Embed the result in the html output.
        data = base64.b64encode(buf.getbuffer()).decode("ascii")
        return {
            "plot": f"<img src='data:image/png;base64,{data}'/>",
            "stats": stats
        }

    def sim_stats(self):
        df = self.run_simulation()
        stats = {}
        all = []
        cum_returns = []
        mr = []
        hw = []
        seized = []
        cpi = []
        vacancy = []
        ren_cost = []
        for element in range(self.n_sims - 1):
            cum_returns.append(df[element]['cum_log_returns'].iloc[-1])
            all.append(df[element]['prices'].iloc[-1])
            mr.append(df[element]['major_repair'].sum())
            hw.append(df[element]['hour_work'].mean())
            seized.append(df[element]['seized'].sum())
            cpi.append(df[element]['cpi_cum_log_returns'].iloc[-1])
            vacancy.append(df[element]['rental_vacancy'].mean())
            ren_cost.append(df[element]['renovation'].sum())

        # Some stats to check if the simulation is working as expected
        stats['cum_returns'] = np.mean(cum_returns)
        stats['prices'] = np.mean(all)
        stats['major_repair'] = np.mean(mr)
        stats['hour_work_week'] = np.mean(hw) / 4
        stats['seized'] = np.mean(seized)
        stats['cpi'] = np.mean(cpi)
        stats['cpi_annualized'] = (1 + np.mean(cpi))**(
            1 / self.expected_holding_period) - 1
        stats['vacancy'] = np.mean(vacancy)
        stats['renovation'] = np.mean(ren_cost)
        return stats

    # This will return an average df from all the simulations
    def avg_df(self):
        dfs = self.cf()
        df = average_dfs(dfs)
        return df

    def benchmark(self):
        df = self.avg_df()
        ticker = self.opp_cost_benchmark
        # Generate simulations for the benchmark

        df['benchmark'] = df['prices'] * (1 + self.benchmark_rate)**(df.index /
                                                                     12)
        return df