import json
import os
import pandas as pd
from pricing_engine.engine import realtime_price
from backend.config import basedir


# Setup IRA Platform Class
class IRA_Platform:

    def __init__(self):
        # Allocation if any
        self.btc_pos = 0  # current BTC position
        self.usd_pos = 0  # current USD position

        # One time fees
        self.setup_fee = 0  # setup fee in USD
        self.setup_fee_as_per_deposit = 0  # setup fee as percentage of deposit
        self.setup_time = 0  # setup time in days
        self.additional_upfront_fees_usd = {"None": 0}
        self.minimum_account = 0  # account minimum size
        self.buy_fee = 0  # Buy fee as % of USD value [ex: 0.01 = 1%]
        self.sell_fee = 0  # Sell fee as % of USD value [ex: 0.01 = 1%]
        self.withdraw_fee = 0  # withdraw fee in USD
        self.spread_usd = 0  # USD Spread to execute a BTC transaction
        self.spread_percent = 0  # percentage spread to execute a BTC transaction

        # Recurring fees
        self.custody_min_fee_usd = 0  # Custody Min Fee in USD
        self.custody_fee_pa = 0  # per annum custody fee on AUM
        self.additional_recurring_fees_usd = [(None, 0)]

        # Descriptive variables
        self.name = None  # Name of IRA provider
        self.bitcoin_only = False  # Bitcoin Only Platform?
        self.IRA_types = {
            'traditional': False,
            'roth': False,
            'SEP': False,
            'simple': False,
            'Solo 401k': False,
        }
        self.in_kind_transfer = False
        self.custodial = False
        self.multisig = False
        self.custodian_administrator = ""  # Custodial or Administrator Name
        self.services = {
            'white_glove': False,
            'prop_research': False,
            'access_to_experts': False,
            'community': False,
            'bitcoin_awards': False,
            'other_services_list': [],
        }

    def allocate_capital(self, amount=None, btc_price=None, year=999):
        # Will allocate everything in cash into BTC
        if btc_price is None:
            btc_price = realtime_price('BTC')['price']
        # Adjust price
        btc_price = btc_price + self.spread_usd * (1 + self.spread_percent)
        # Allocates into a new IRA
        if amount is None:
            amount = self.usd_pos

        # If there's no amount specified and no usd to allocate
        # then there's no need to allocate
        if amount == 0 and self.usd_pos == 0:
            return ({
                'gross_amount': 0,
                'fees': 0,
                'net_amount': 0,
                'btc_price_with_fee': None,
            })

        # after fee usd = the amount available to buy after paying fees
        after_fee_usd = amount * (1 - self.buy_fee)

        # Setup fees only happen at inception
        if year == 0:
            after_fee_usd = after_fee_usd - self.setup_fee
            after_fee_usd = after_fee_usd - (self.usd_pos *
                                             self.setup_fee_as_per_deposit)
        # Remove additional fees
        for key, fee in self.additional_upfront_fees_usd.items():
            after_fee_usd = after_fee_usd - fee

        # Allocate after-fees amount into BTC
        btc = after_fee_usd / btc_price

        # Zero out USD position
        self.usd_pos = self.usd_pos - amount

        # Allocate to current BTC position
        self.btc_pos = self.btc_pos + btc
        return ({
            'contribution_btc_amount': btc,
            'contribution_gross_amount': amount,
            'contribution_fees': amount - after_fee_usd,
            'contribution_net_amount': after_fee_usd,
            'contribution_btc_price_with_fee': btc_price,
        })

    def unwind_btc(self, btc_pos=None, btc_price=None):
        # Returns the dollar amount after unwinding
        # and closing the IRA
        # Sell BTC:
        # Adjust price to account for spreads
        if btc_price is None:
            btc_price = realtime_price('BTC')['price']
        # If no position specified, liquidate all BTCs
        if btc_pos is None:
            btc_pos = self.btc_pos
        btc_price = (btc_price - self.spread_usd) * (1 - self.spread_percent)
        usd_proceeds = btc_pos * (1 - self.sell_fee) * btc_price
        # Pay withdraw fees
        usd_proceeds = usd_proceeds - self.withdraw_fee
        # Zero out BTC position
        self.btc_pos = 0
        # Allocate to cash
        if self.usd_pos is None:
            self.usd_pos = 0
        self.usd_pos += usd_proceeds
        return usd_proceeds

    def future_positions(self,
                         years,
                         btc_price,
                         btc_growth_pa,
                         contribution=0):
        # Creates a future position balance of BTC for the next n years
        yearly_positions = []
        total_fees_cum = 0
        fees_in_btc_cum = 0
        for year in range(0, years + 1):
            # assume client needs to deposit the cash to pay fees annually
            year_dict = {'year': year, 'btc_price': btc_price}

            # Include placeholder variables
            year_dict['contribution_gross'] = 0
            year_dict['contribution_net_amount'] = 0
            year_dict['contribution_btc_amount'] = 0

            # Calculate Fees
            # Custody fee
            custody_fee = self.custody_fee_pa * self.btc_pos * btc_price
            # Check if above min fee, if not charge minimum fee in USD
            if custody_fee < self.custody_min_fee_usd:
                custody_fee = self.custody_min_fee_usd
            year_dict['custody_fee_usd'] = custody_fee
            # Other recurring fees
            other_fees = 0
            for fee in self.additional_recurring_fees_usd:
                if fee is not None and fee != 'None':
                    other_fees += fee[1]
            year_dict['other_fees_usd'] = other_fees

            # Include contributions
            if year > 0:
                contribution = 0 if contribution is None else contribution
                year_dict['contribution_gross'] = contribution
                # Allocate contributions to BTC
                if contribution > 0:
                    self.usd_pos += contribution
                    allocate = self.allocate_capital(amount=contribution,
                                                     btc_price=btc_price,
                                                     year=year)
                    # merge the results into year_dict
                    year_dict = {**year_dict, **allocate}

            year_dict['total_fees'] = other_fees + custody_fee

            # Add contribution fees to total fees of year
            if 'contribution_fees' in year_dict:
                year_dict['total_fees'] += year_dict['contribution_fees']

            total_fees_cum += other_fees + custody_fee
            year_dict['total_fees_cum'] = total_fees_cum

            # Opportunity cost of fees
            year_dict['fees_in_btc'] = (year_dict['total_fees'] / btc_price)
            fees_in_btc_cum += year_dict['fees_in_btc']
            year_dict['fees_in_btc_cum'] = fees_in_btc_cum
            year_dict['opp_cost_usd'] = fees_in_btc_cum * btc_price

            year_dict['btc_pos'] = self.btc_pos
            year_dict['port_pos'] = self.btc_pos * btc_price
            year_dict['usd_pos'] = self.usd_pos

            # Increase / Decrease BTC price
            btc_price = btc_price * btc_growth_pa

            yearly_positions.append(year_dict)

        return (yearly_positions)

    def to_json(self):
        return (json.dumps(self.__dict__, default=str))


def load_competitor_data(html=False, json_export=False):
    # Loads competitive matrix from json file
    filename = os.path.join(basedir, 'static/json_files/ira_matrix.json')
    with open(filename, 'r') as handle:
        competitive_matrix = json.load(handle)
        # Export raw json data (not an instance of IRA)
        if json_export is True:
            return competitive_matrix
    if html is True:
        pd.set_option('float_format', lambda x: "%.2f" % x)
        comp_df = pd.DataFrame(competitive_matrix).T
        cols = [
            "IRA Service Name", "Setup Fee (USD)",
            "Minimum Account Value (USD)", "Setup Time (Days)", "Buy Fee (%)",
            "Sell Fee (%)", "Withdraw Fee (USD)", "Custody Fee (%)",
            "Min Custody Fee (USD)", "Bitcoin Only", "Custodial", "Multisig",
            "Custody Details"
        ]
        comp_df = comp_df[cols]
        html_table = comp_df.to_html(justify='center',
                                     table_id='comp_table',
                                     index=False,
                                     classes=['table', 'table-small'])
        return (html_table)

    # Create instances of each IRA
    ira_list = []
    for ira, value in competitive_matrix.items():
        tmp_ira = IRA_Platform()
        # Loads into instance
        tmp_ira.name = value['IRA Service Name']
        tmp_ira.setup_fee = value["Setup Fee (USD)"]
        try:
            tmp_ira.setup_fee_as_per_deposit = value[
                "Setup Fee (as % of deposit)"]
        except KeyError:
            tmp_ira.setup_fee_as_per_deposit = 0
        tmp_ira.setup_time = value["Setup Time (Days)"]
        tmp_ira.additional_upfront_fees_usd = value[
            "Additional Upfront Fees (USD)"]
        tmp_ira.minimum_account = value["Minimum Account Value (USD)"]
        tmp_ira.buy_fee = value["Buy Fee (%)"]
        tmp_ira.sell_fee = value["Sell Fee (%)"]
        tmp_ira.withdraw_fee = value["Withdraw Fee (USD)"]

        tmp_ira.custody_min_fee_usd = value["Min Custody Fee (USD)"]
        tmp_ira.custody_fee_pa = value["Custody Fee (%)"]
        tmp_ira.additional_recurring_fees_usd = value[
            "Additional Recurring Fees (USD)"]

        tmp_ira.bitcoin_only = value["Bitcoin Only"]
        tmp_ira.IRA_types = value["IRA Types"]
        tmp_ira.in_kind_transfer = value["In-kind transfer"]
        tmp_ira.custodial = value["Custodial"]
        tmp_ira.multisig = value["Multisig"]
        tmp_ira.custodian_administrator = value["Custody Details"]
        tmp_ira.services = value["Services"]
        tmp_ira.spread_usd = value["Spread (USD)"]
        tmp_ira.spread_percent = value["Spread (%)"]

        ira_list.append(tmp_ira)

    return (ira_list)


def return_json_name(ira_name):
    ira_list = load_competitor_data(json_export=True)
    for key, values in ira_list.items():
        if values["IRA Service Name"] == ira_name:
            return key


def load_ira(ira_name, json_export=True):
    ira_list = load_competitor_data(json_export=json_export)
    if json_export is True:
        for key, values in ira_list.items():
            if values["IRA Service Name"] == ira_name:
                return values
    else:
        for ira in ira_list:
            if ira.name == ira_name:
                return ira

    return None


def ira_run_comparison(ira, btc, cash, years, btc_chg, contribution=0):
    # Get latest BTC price
    try:
        btc_price = realtime_price('BTC')['price']
    except TypeError:
        return None

    # Run comparison between this IRA and others
    return_dict = {
        'ira': ira,
        'initial_btc': btc,
        'initial_cash': cash,
        'btc_price': btc_price,
        'years': years,
        'btc_chg': btc_chg,
        'contribution': contribution
    }

    # Load all IRAs
    iras = load_competitor_data()

    # load current ira and store
    return_dict['current_ira_json'] = load_ira(ira, json_export=True)
    if ira == 'This is a new IRA':
        current_ira = IRA_Platform()
    else:
        current_ira = load_ira(ira, json_export=False)

    # allocate positions to current ira
    current_ira.btc_pos = btc
    current_ira.usd_pos = cash

    # Calculate price with spread
    btc_sell_price = (btc_price - current_ira.spread_usd) * (
        1 - current_ira.spread_percent) * (1 - current_ira.sell_fee)
    return_dict['btc_sell_price'] = btc_sell_price
    btc_buy_price = (btc_price + current_ira.spread_usd) * (
        1 + current_ira.spread_percent) * (1 + current_ira.buy_fee)
    return_dict['btc_buy_price'] = btc_buy_price

    # Calculate future cash flows for this ira and store
    return_dict['current_ira_future_cf'] = current_ira.future_positions(
        years=years,
        btc_price=btc_price,
        btc_growth_pa=btc_chg,
        contribution=contribution)

    # Save current portfolio position before any unwinds
    for element in return_dict['current_ira_future_cf']:
        if element['year'] == 0:
            current_port_value = element['port_pos']
            initial_btc_pos = element['btc_pos']

    # Calculate proceeds after unwinding this IRA
    usd_proceeds = current_ira.unwind_btc(btc_pos=initial_btc_pos)
    return_dict['usd_proceeds'] = usd_proceeds

    return_dict['unwind'] = {
        'before_unwind': current_port_value,
        'after_unwind': usd_proceeds,
        'cost_unwind': current_port_value - usd_proceeds,
        'fees': {
            'spread_usd': current_ira.spread_usd,
            'spread_percent': current_ira.spread_percent,
            'buy_fee': current_ira.buy_fee,
            'sell_fee': current_ira.sell_fee,
            'btc_price_gross': btc_price,
            'btc_buy_price': btc_buy_price,
            'btc_sell_price': btc_sell_price,
            'withdraw_fee': current_ira.withdraw_fee,
        }
    }

    # Run allocation into all other IRAs
    new_iras_future_cf = {}
    for ira in iras:
        ira.btc_pos = 0
        ira.usd_pos = usd_proceeds
        ira.allocate_capital(btc_price=btc_price)
        result = ira.future_positions(years=years,
                                      btc_price=btc_price,
                                      btc_growth_pa=btc_chg,
                                      contribution=contribution)
        new_iras_future_cf[ira.name] = result

    return_dict['new_iras_future_cf'] = new_iras_future_cf

    return (return_dict)


# Create a waterfall chart comparing the IRAs
def ira_run_waterfall(data, new_ira='Swan IRA'):
    # data to return:
    # . Initial Position in BTC
    # . Initial Position in USD
    # . Price appreciation of BTC in USD
    # . Contributions
    # . Trading Fees
    # . Difference in Trading fees (every contribution)
    # . Price appreciation in Contributions
    # . If fees are lower, deposit into BTC
    # . If fees are higher, sell BTC
    # . Custody Fees
    # . Unwind Cost

    # IRA Names for comparison
    current_ira = data['results']['current_ira_json']['IRA Service Name']

    # Create Waterfall Data
    total_years = data['results']['years']
    last_year_dic = (next(item
                          for item in data['results']['current_ira_future_cf']
                          if item["year"] == total_years))

    initial_position_btc = data['results']['initial_btc']
    initial_cash = data['results']['initial_cash']
    if initial_cash is None:
        initial_cash = 0
    initial_btc_price = data['results']['btc_price']
    initial_total_position_usd = ((initial_position_btc * initial_btc_price) +
                                  initial_cash)

    final_btc_price = last_year_dic['btc_price']
    final_btc_position = last_year_dic['btc_pos']
    final_total_position_usd = ((final_btc_position * final_btc_price) +
                                initial_cash)
    btc_price_appreciation = (initial_position_btc *
                              (final_btc_price - initial_btc_price))

    gross_contributions = sum([
        item['contribution_gross']
        for item in data['results']['current_ira_future_cf']
    ])
    net_contributions = sum([
        item['contribution_net_amount']
        for item in data['results']['current_ira_future_cf']
    ])
    fees_on_contributions = gross_contributions - net_contributions
    btc_contributions = sum([
        item['contribution_btc_amount']
        for item in data['results']['current_ira_future_cf']
    ])

    contributions_appreciation = ((btc_contributions * final_btc_price) -
                                  net_contributions)

    gross_balance = (initial_total_position_usd + btc_price_appreciation +
                     gross_contributions - fees_on_contributions +
                     contributions_appreciation)

    # Calculate Custody Fees paid
    custody_fees = sum([
        item['custody_fee_usd']
        for item in data['results']['current_ira_future_cf']
    ])
    other_fees = sum([
        item['other_fees_usd']
        for item in data['results']['current_ira_future_cf']
    ])

    net_balance = gross_balance - custody_fees - other_fees

    # Unwind at year 10
    old_spread_p = data['results']['current_ira_json']['Spread (%)']
    old_spread_usd = data['results']['current_ira_json']['Spread (USD)']
    old_sell_fee = data['results']['current_ira_json']['Sell Fee (%)']
    unwind_costs_at_end = (net_balance - old_spread_usd) * (old_spread_p +
                                                            old_sell_fee)
    net_after_unwind = net_balance - unwind_costs_at_end

    # Error Check
    if round(gross_balance, 1) != round(final_total_position_usd, 1):
        raise Exception("Calculation Error on Gross Balance. " +
                        f"Gross Balance: {gross_balance} is not equal to " +
                        f"{final_total_position_usd}")

    # Load original IRA Data into a DF
    original_ira_data = data['results']['current_ira_future_cf']
    old_df = pd.DataFrame(original_ira_data)
    old_df = old_df.set_index('year')

    # Add missing columns to df
    if 'contribution_fees' not in old_df:
        old_df['contribution_fees'] = 0

    # Load New IRA Data + into a DF
    new_ira_json = load_ira(new_ira)
    new_ira_data = data['results']['new_iras_future_cf'][new_ira]
    new_df = pd.DataFrame(new_ira_data)
    new_df = new_df.set_index('year')

    # Add missing columns to df
    if 'contribution_fees' not in new_df:
        new_df['contribution_fees'] = 0

    # Calculate the difference in Custody Fees Every year
    new_df['old_ira_custody_fees'] = old_df['custody_fee_usd']
    new_df['old_ira_other_fees'] = old_df['other_fees_usd']
    new_df['old_ira_total_fees'] = (new_df['old_ira_custody_fees'] +
                                    new_df['old_ira_other_fees'])

    new_df['diff_in_fees'] = (new_df['old_ira_total_fees'] -
                              new_df['custody_fee_usd'] -
                              new_df['other_fees_usd'])

    spread_p = new_ira_json['Spread (%)']
    spread_usd = new_ira_json['Spread (USD)']
    buy_fee = new_ira_json['Buy Fee (%)']
    sell_fee = new_ira_json['Sell Fee (%)']

    new_df['btc_buy_price'] = ((new_df['btc_price'] * (1 + spread_p) *
                                (1 + buy_fee)) + spread_usd)
    new_df['BTC_bought_with_diff_in_fees'] = new_df['diff_in_fees'] / new_df[
        'btc_buy_price']

    # Update Positions
    new_df['new_btc_pos'] = new_df['btc_pos'] + new_df[
        'BTC_bought_with_diff_in_fees']
    new_df['new_port_pos'] = new_df['new_btc_pos'] * new_df['btc_price']

    # Create Waterfall Analysis for new IRA Service
    # Check if roll costs match
    roll_costs = data['results']['unwind']['cost_unwind']

    # Move to new IRA
    invested_ira_gross = (initial_total_position_usd - roll_costs)
    setup_fee_at_new_ira = new_ira_json['Setup Fee (USD)']
    try:
        setup_fee_at_new_ira_percentage = new_ira_json[
            'Setup Fee (as % of deposit)'] * invested_ira_gross
    except KeyError:
        setup_fee_at_new_ira_percentage = 0
    new_ira_invested_net = new_df.loc[0]['port_pos']
    new_ira_net_contributions = new_df['contribution_net_amount'].sum()
    new_ira_btc_appreciation = (new_df.loc[0]['btc_pos'] *
                                (final_btc_price - initial_btc_price))
    new_ira_contributions_appreciation = (
        (new_df['contribution_btc_amount'].sum() * final_btc_price) -
        new_ira_net_contributions)
    new_ira_fees_on_contributions = (gross_contributions -
                                     new_df['contribution_net_amount'].sum())
    new_ira_gross_balance = (new_ira_invested_net + new_ira_btc_appreciation +
                             gross_contributions -
                             new_ira_fees_on_contributions +
                             new_ira_contributions_appreciation)
    new_ira_custody_fees = new_df['custody_fee_usd'].sum()
    new_ira_other_fees = new_df['other_fees_usd'].sum()
    new_ira_net_balance = (new_ira_gross_balance - new_ira_custody_fees -
                           new_ira_other_fees)
    new_ira_fee_difference = new_df['diff_in_fees'].sum()
    btc_diff_fees = new_df['BTC_bought_with_diff_in_fees'].sum()

    new_balance_end = new_df.iloc[-1]['new_port_pos']

    # Unwind at year 10
    new_spread_p = new_ira_json['Spread (%)']
    new_spread_usd = new_ira_json['Spread (USD)']
    new_sell_fee = new_ira_json['Sell Fee (%)']
    new_unwind_costs_at_end = (new_balance_end -
                               new_spread_usd) * (new_spread_p + new_sell_fee)
    new_net_after_unwind = new_balance_end - new_unwind_costs_at_end

    # More data
    old_df['port_pos_net'] = old_df['btc_pos'] * old_df['btc_price']
    new_df['port_pos_net'] = new_df['btc_pos'] * new_df['btc_price']

    # Create HighCharts Data for Current IRA
    old_high_charts_series = [{
        'name': 'Initial</br>Portfolio</br>Value',
        'y': initial_total_position_usd
    }, {
        'name': 'BTC</br>Price</br>Appreciation',
        'y': btc_price_appreciation,
    }, {
        'name': 'Gross</br>Contributions',
        'y': gross_contributions,
    }, {
        'name': 'Fees</br>on</br>Contributions',
        'y': -fees_on_contributions,
    }, {
        'name': 'BTC</br>price</br>appreciation</br>on Contributions',
        'y': contributions_appreciation,
    }, {
        'name': 'Gross</br>Balance',
        'y': gross_balance,
        'isSum': True,
        'color': '#31597F'
    }, {
        'name': 'Custody</br>Fees',
        'y': -custody_fees,
    }, {
        'name': 'Other</br>Fees',
        'y': -other_fees,
    }, {
        'name': 'Net</br>Balance',
        'y': net_balance,
        'isSum': True,
        'color': '#31597F'
    }, {
        'name': f'Unwind</br>Costs</br>at Year</br>{str(total_years)}',
        'y': -unwind_costs_at_end,
    }, {
        'name': 'Net</br>Balance</br>after Unwind',
        'y': net_after_unwind,
        'isSum': True,
        'color': '#31597F'
    }]

    new_high_charts_series = [{
        'name': 'Initial</br>Portfolio</br>Value',
        'y': initial_total_position_usd
    }, {
        'name': 'Roll</br>Costs',
        'y': -roll_costs,
    }, {
        'name': 'Invested</br>after</br>Costs',
        'y': new_ira_invested_net,
        'isSum': True,
        'color': '#31597F'
    }, {
        'name': 'BTC</br>Price</br>Appreciation',
        'y': new_ira_btc_appreciation,
    }, {
        'name': 'Gross</br>Contributions',
        'y': gross_contributions,
    }, {
        'name': 'Fees</br>on</br>Contributions',
        'y': -new_ira_fees_on_contributions,
    }, {
        'name': 'BTC</br>price</br>appreciation</br>on Contributions',
        'y': new_ira_contributions_appreciation,
    }, {
        'name': 'Gross</br>Balance',
        'y': new_ira_gross_balance,
        'isSum': True,
        'color': '#31597F'
    }, {
        'name': 'Custody</br>Fees',
        'y': -new_ira_custody_fees,
    }, {
        'name': 'Other</br>Fees',
        'y': -new_ira_other_fees,
    }, {
        'name': 'Net</br>Balance',
        'y': new_ira_net_balance,
        'isSum': True,
        'color': '#31597F'
    }, {
        'name': 'Invested</br>Fee</br>Savings',
        'y': new_ira_fee_difference,
        'color': '#7B96B0'
    }, {
        'name': 'Net Balance</br>including</br>Fee Difference',
        'y': new_balance_end,
        'isSum': True,
        'color': '#31597F'
    }, {
        'name': f'Unwind</br>Costs</br>at Year</br>{str(total_years)}',
        'y': -new_unwind_costs_at_end,
    }, {
        'name': 'Net</br>Balance</br>after Unwind',
        'y': new_net_after_unwind,
        'isSum': True,
        'color': '#31597F'
    }]

    btc_price_data = {
        'categories': list(range(0, total_years + 1)),
        'data': new_df['btc_price'].to_list()
    }

    position_data = {
        'new_name': new_ira,
        'old_name': current_ira,
        'categories': list(range(0, total_years + 1)),
        'new_IRA_btc': new_df['new_btc_pos'].to_list(),
        'current_IRA_btc': old_df['btc_pos'].to_list(),
        'new_IRA_usd': new_df['port_pos_net'].to_list(),
        'current_IRA_usd': old_df['port_pos_net'].to_list(),
    }

    # Include fee data in the dataframes
    new_df['roll_fee'] = 0
    new_df.at[0, 'roll_fee'] = roll_costs
    new_df['unwind_at_end'] = 0
    new_df.at[total_years, 'unwind_at_end'] = new_unwind_costs_at_end
    old_df['unwind_at_end'] = 0
    old_df.at[total_years, 'unwind_at_end'] = unwind_costs_at_end

    fee_data = {
        'new_name':
        new_ira,
        'old_name':
        current_ira,
        'categories':
        list(range(0, total_years + 1)),
        'old_IRA_custody':
        old_df['custody_fee_usd'].cumsum().to_list(),
        'old_IRA_other':
        old_df['other_fees_usd'].cumsum().to_list(),
        'old_IRA_cont_fee':
        old_df['contribution_fees'].cumsum().to_list(),
        'old_IRA_unwind':
        old_df['unwind_at_end'].cumsum().to_list(),
        'new_IRA_other':
        new_df['other_fees_usd'].cumsum().to_list(),
        'new_IRA_roll_fee':
        new_df['roll_fee'].cumsum().to_list(),
        'new_IRA_cont_fee':
        new_df['contribution_fees'].cumsum().to_list(),
        'new_IRA_custody':
        new_df['custody_fee_usd'].cumsum().to_list(),
        'new_IRA_unwind':
        new_df['unwind_at_end'].cumsum().to_list(),
        'btc_bought_fees':
        new_df['BTC_bought_with_diff_in_fees'].cumsum().to_list(),
    }

    waterfall = {
        'Current IRA':
        current_ira,
        'Years':
        total_years,
        'Initial Position (USD)':
        initial_total_position_usd,
        'Initial Position (BTC)':
        initial_position_btc,
        'Initial Cash Position (USD)':
        initial_cash,
        'BTC Appreciation':
        btc_price_appreciation,
        'Final BTC Price':
        final_btc_price,
        'Contributions (gross)':
        gross_contributions,
        'Fees on Contributions':
        fees_on_contributions,
        'Contributions Appreciation':
        contributions_appreciation,
        'Gross Balance':
        gross_balance,
        'Custody Fees':
        custody_fees,
        'Other Fees':
        other_fees,
        'Net Balance':
        net_balance,
        'Unwind Costs at End':
        unwind_costs_at_end,
        'Net After Unwind at End':
        net_after_unwind,
        'New IRA':
        new_ira,
        'Roll Costs':
        roll_costs,
        'Invested at New IRA Gross of Fees':
        invested_ira_gross,
        'Setup Fee at New IRA (USD)':
        (setup_fee_at_new_ira + setup_fee_at_new_ira_percentage),
        'Purchase Fee at New IRA (%)': (new_ira_json['Buy Fee (%)']),
        'Purchase Fee at New IRA (USD)':
        ((old_df.loc[0]['port_pos'] - roll_costs) *
         new_ira_json['Buy Fee (%)']),
        'Invested at New IRA Net of Fees':
        new_ira_invested_net,
        'New IRA Initial Position (BTC)':
        new_df.loc[0]['btc_pos'],
        'New IRA BTC Appreciation':
        new_ira_btc_appreciation,
        'New IRA Contributions (gross)':
        gross_contributions,
        'New IRA Fees on Contributions':
        new_ira_fees_on_contributions,
        'New IRA Contributions Appreciation':
        new_ira_contributions_appreciation,
        'New IRA Gross Balance':
        new_ira_gross_balance,
        'New IRA Custody Fees':
        new_ira_custody_fees,
        'New IRA Other Fees':
        new_ira_other_fees,
        'New IRA Net Balance':
        new_ira_net_balance,
        'New IRA Fee Difference':
        new_ira_fee_difference,
        'New IRA BTC Bought with Fee Difference':
        btc_diff_fees,
        'Net Balance including Fee Difference':
        new_balance_end,
        'New IRA Unwind Costs at End':
        new_unwind_costs_at_end,
        'New IRA Net After Unwind at End':
        new_net_after_unwind,
        'HighCharts_Data_Old':
        json.dumps(old_high_charts_series),
        'HighCharts_Data_New':
        json.dumps(new_high_charts_series, default=float),
        'btc_forecast':
        json.dumps(btc_price_data, default=float),
        'position_data':
        json.dumps(position_data, default=float),
        'fee_data':
        json.dumps(fee_data, default=float),
    }

    return waterfall
