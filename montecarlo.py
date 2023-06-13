import os
from backend.utils import file_created_today, pickle_it
from backend.config import home_dir, basedir
import numpy as np
import json
import pandas as pd
import concurrent.futures
from scipy import stats
from scipy.optimize import minimize
from scipy.stats import genhyperbolic
import base64
from io import BytesIO
from matplotlib.figure import Figure
import seaborn as sns
from matplotlib.ticker import FuncFormatter
from matplotlib.patches import Rectangle
from backend.decorators import MWT, timing
from backend.allocator import annualization_factor
from backend.ansi_management import jformat


def load_distributions():
    filename = os.path.join(basedir, 'static/json_files/distributions.json')
    with open(filename, 'r') as handle:
        data = json.load(handle)
    return (data)


def estimate_distribution(data, distribution):
    """
    Estimate distribution parameters and calculate AIC

    Args:
        data (pd.Series): data
        distribution (object): distribution

    Returns:
        float: AIC
    """
    # Set initial values
    init_params = distribution.fit(data)

    # Estimate parameters
    params_estimate = minimize(negative_log_likelihood,
                               init_params,
                               args=(data, distribution)).x

    # Calculate Log-Likelihood
    loglike = -negative_log_likelihood(params_estimate, data, distribution)

    # Calculate AIC
    aic_val = 2 * len(params_estimate) - 2 * loglike

    return aic_val


# Define the function to calculate the negative log-likelihood of a distribution.
def negative_log_likelihood(params, data, distribution):
    """
    Negative log-likelihood function

    Args:
        params (list): parameters of the distribution
        data (pd.Series): data
        distribution (object): distribution

    Returns:
        float: negative log-likelihood
    """
    if distribution.name in ['t', 'genhyperbolic']:
        # Degrees of freedom must be positive
        if params[-1] <= 0:
            return np.inf

    # Estimate Log-Likelihood
    loglike = np.sum(distribution.logpdf(data, *params))

    # Convert to Negative Log-Likelihood
    return -loglike


# Function to Calculate Rolling Returns
def prep_df(df, n):
    """
    This function calculates the n-days rolling returns
    """
    df['close'] = df['close'].astype(float)
    df['close'] = df['close'].dropna()
    df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
    # Drop zeros - otherwise weekends would impact the distribution of stocks
    df = df.loc[df['log_returns'] != 0]
    df[f'{n}_day_rolling_return'] = df['log_returns'].rolling(n).sum()
    return df


def fit_distribution(dist_name, df, n, method):
    try:
        dist = getattr(stats, dist_name)
        param = dist.fit(df[f'{n}_day_rolling_return'].dropna())
        if method == 'ks':
            a = stats.kstest(df[f'{n}_day_rolling_return'].dropna(),
                             dist_name,
                             args=param)
            return (dist_name, a[0], a[1], None)
        elif method == 'aic':
            dist = getattr(stats, dist_name)
            data = df[f'{n}_day_rolling_return'].dropna()
            aic_val = estimate_distribution(data, dist)
            return (dist_name, None, None, aic_val)
    except Exception:
        return None


def best_fit(ticker, df, n=1, force=False, method='ks'):
    # try to load file
    filename = os.path.join(
        home_dir, ticker + "_" + method + "_" + str(n) + '_best_fit_data.pkl')
    # Check if file is fresh
    if force is False and file_created_today(filename, hours=12):
        data = pickle_it('load', filename)
        return (data)

    # Function to determine the best fit for a dataframe
    # df is a dataframe that has a column named 'close'
    # Will return a df with the best fit distributions
    # sorted by p-value
    df = prep_df(df, n)

    # Load all distributions from json
    # dist_names = load_distributions().keys()
    # Or keep it simple to expedite and only include
    # relevant distributions
    dist_names = [
        'genhyperbolic', 't', 'johnsonsu', 'norminvgauss', 'laplace',
        'gennorm', 'dweibull', 'dgamma', 'loglaplace'
    ]

    # Use a ThreadPoolExecutor to fit the distributions in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(fit_distribution, dist_name, df, n, method)
            for dist_name in dist_names
        ]

    # Collect the results as they become available
    results = [
        f.result() for f in concurrent.futures.as_completed(futures)
        if f.result() is not None
    ]

    results_df = pd.DataFrame(
        results, columns=['Distribution', 'KS Statistic', 'P-Value', 'AIC'])

    if method == 'ks':
        # sort df by KS Statistic
        results_df.sort_values(by=['KS Statistic'],
                               ascending=True,
                               inplace=True)
    elif method == 'aic':
        # sort df by AIC
        results_df = results_df.dropna(subset=['AIC'])
        results_df.sort_values(by=['AIC'], ascending=True, inplace=True)

    pickle_it('save', filename, results_df)
    return (results_df)


@MWT(timeout=60 * 60 * 6)
def get_stats(df, dist_name, n=1):
    return_dict = {}
    df = prep_df(df, n)
    vol = df[f'{n}_day_rolling_return'].std()
    mean = df[f'{n}_day_rolling_return'].mean()
    geomean = np.exp(df[f'{n}_day_rolling_return'].mean()) - 1
    dist = getattr(stats, dist_name)
    param = dist.fit(df[f'{n}_day_rolling_return'].dropna())
    # Here are the params returned by the fit method:
    # lambda: This is the shape parameter. It dictates the overall shape of the distribution - where data is more likely to be found. It's a bit like the boss of a sculptor, guiding the overall form that the sculpture should take.
    # alpha: This is the first tail parameter. It influences how "fat" or "thin" the tails of the distribution are. If you think of the distribution as a mountain, alpha influences how gently or abruptly the mountain slopes down to the plains.
    # beta: This is the skewness parameter. It determines whether there's more data on one side than the other, and if so, which side that is. If beta was a wind blowing over our mountain from the previous example, a strong enough wind could make the mountain lean more towards one side.
    # delta: This is the scale parameter. It affects how spread out the data is. A larger delta would stretch our mountain horizontally, making it wider, whereas a smaller delta would squeeze the mountain, making it more narrow.
    # mu: This is the location parameter. It shifts the entire distribution left or right along the x-axis. If our mountain could be picked up and moved, mu would be the GPS coordinate we want the mountain to be located at.
    returns = df[f'{n}_day_rolling_return'].dropna()
    _, p_value = stats.kstest(returns, dist_name, args=param)
    annualization = annualization_factor(df)

    return_dict = {
        'start_date': df.index.min(),
        'end_date': df.index.max(),
        'dist_name': dist_name,
        'n': n,
        'annualization': annualization,
        'p_value': p_value,
        'mean': mean,
        'mean_annualized': (1 + mean)**annualization - 1,
        'vol': vol,
        'vol_annualized': vol * annualization**.5,
        'geomean': geomean,
        'geomean_annualized': (1 + geomean)**annualization - 1,
        'skewness': df[f'{n}_day_rolling_return'].skew(),
        'kurtosis': df[f'{n}_day_rolling_return'].kurt()
    }

    return (return_dict)


def histogram_image(df,
                    limit=0.2,
                    n=1,
                    figsize=(8, 5),
                    quantile=0.025,
                    binwidth=0.1):
    # Generate the figure **without using pyplot**.
    fig = Figure(figsize=figsize)
    ax = fig.subplots()

    df = prep_df(df, n)

    # Prepare data
    data = df[f'{n}_day_rolling_return'] * 100
    lower = data.quantile(quantile)
    upper = data.quantile(1 - quantile)

    # Make the histogram using seaborn, provide a handle to the current Axes (ax)
    bar_color = "#5fba7d"
    edge_color = "#FFFFFF"
    sns.histplot(
        data,
        stat="density",
        kde=False,
        ax=ax,
        color=bar_color,
        edgecolor=edge_color,
        linewidth=1,
        binwidth=binwidth * 100,
    )

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

    ax.set_title(f'Histogram of log returns - {n} day(s) rolling')
    ax.set_xlim(-limit * 100, limit * 100)

    # Labels
    ax.set_xlabel(f"Rolling {n} days of returns (%)")
    ax.set_ylabel("Probability Density")

    # Horizontal gridlines
    ax.grid(axis='y', color='white', linestyle='dashed', alpha=0.2)
    ax.set_axisbelow(True)  # Set gridlines behind other graph elements

    # Format x-axis labels as percentages
    formatter = FuncFormatter(lambda x, pos: f'{x:.2f}%')
    ax.xaxis.set_major_formatter(formatter)

    # Format y-axis labels as percentages
    formatter = FuncFormatter(lambda x, pos: f'{((x*100)):.2f}%')
    ax.yaxis.set_major_formatter(formatter)

    # Draw rectangle and annotate
    rectangle = Rectangle(
        (lower, 0),
        upper - lower,
        ax.get_ylim()[1],
        fill=False,  # This means that the rectangle will not be filled
        edgecolor='#f0e68c',
        linewidth=4)
    ax.add_patch(rectangle)
    # Annotate
    text = f'{(100 - (quantile * 2 * 100)):.2f}% of the returns were between {lower:.2f}% and {upper:.2f}%'
    text_x = lower + (upper - lower) / 2  # Center of the rectangle
    text_y = ax.get_ylim()[1]  # Top of the plot
    offset_points = (0, -10)  # Offset in points: (horizontal, vertical)
    ax.annotate(text,
                xy=(text_x, text_y),
                xycoords='data',
                xytext=offset_points,
                textcoords='offset points',
                color='#f0e68c',
                ha='center',
                va='top',
                fontsize=12)

    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format="png", transparent=True)

    # Embed the result in the html output.
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    return f"<img src='data:image/png;base64,{data}'/>"


def best_fit_image(df,
                   dist_name,
                   limit=0.2,
                   n=1,
                   figsize=(8, 5),
                   binwidth=0.001):
    # Generate the figure **without using pyplot**.
    fig = Figure(figsize=figsize)
    ax = fig.subplots()

    df = prep_df(df, n)

    # Prepare data
    returns = df[f'{n}_day_rolling_return'].dropna()

    # Make the histogram using seaborn's histplot() function
    bar_color = "#5fba7d"
    edge_color = "#FFFFFF"
    sns.histplot(returns,
                 stat="density",
                 kde=False,
                 ax=ax,
                 color=bar_color,
                 edgecolor=edge_color,
                 linewidth=1,
                 binwidth=binwidth)

    # Best Fit distribution and plot
    dist = getattr(stats, dist_name)
    params = dist.fit(returns)
    x = np.linspace(min(returns), max(returns), 10000)
    pdf_fitted = dist.pdf(x, *params)
    ax.fill_between(x, pdf_fitted, color='#7dabff', alpha=0.3)
    # Overlay a line chart with the same y-values in white
    ax.plot(x, pdf_fitted, color='white', linewidth=3, alpha=0.9)

    # Set background color
    fig.patch.set_facecolor('#404040')  # Set entire figure's background color
    ax.set_facecolor('#404040')  # Set chart area color

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

    ax.set_title(
        f'Histogram of log returns - {n} day(s) rolling\nBest fit {dist_name} distribution'
    )
    ax.set_xlim(-limit, limit)

    # Labels
    ax.set_xlabel(f"Rolling {n} days of returns")
    ax.set_ylabel("Probability Density")

    # Horizontal gridlines
    ax.grid(axis='y', color='white', linestyle='dashed', alpha=0.2)
    ax.set_axisbelow(True)  # Set gridlines behind other graph elements

    # Format x-axis labels as percentages
    formatter = FuncFormatter(lambda x, pos: f'{(x*100):.2f}%')
    ax.xaxis.set_major_formatter(formatter)

    # Format y-axis labels as percentages
    formatter = FuncFormatter(lambda x, pos: f'{(x):.2f}%')
    ax.yaxis.set_major_formatter(formatter)

    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format="png", transparent=True)

    # Embed the result in the html output.
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    return f"<img src='data:image/png;base64,{data}'/>"


def generate_monte_carlo_simulations(df, n, n_sims, n_days, dist_name):
    # Prepare data
    df = prep_df(df, n)
    returns = df[f'{n}_day_rolling_return'].dropna()
    # Best Fit distribution and plot
    dist = getattr(stats, dist_name)
    params = dist.fit(returns)
    sim_returns = dist.rvs(*params, size=(n_days, n_sims))
    return sim_returns


def project_future_prices(last_price, sim_returns):
    # First, compute the cumulative log returns
    cumulative_log_returns = np.cumsum(sim_returns, axis=0)
    # Then exponentiate to get relative price changes
    relative_prices = np.exp(cumulative_log_returns)
    # Finally, multiply by the last price to get absolute prices
    sim_prices = last_price * relative_prices

    return sim_prices, sim_returns


def run_montecarlo(df, n=1, n_sims=100, n_days=365, dist_name='genhyperbolic'):
    # Use log returns instead of arithmetic returns
    df[f'{n}_day_rolling_return'] = np.log(df['close'] / df['close'].shift(n))
    sim_returns = generate_monte_carlo_simulations(df, n, n_sims, n_days,
                                                   dist_name)
    last_price = df['close'][-1]
    sim_prices, sim_returns = project_future_prices(last_price, sim_returns)
    return (sim_prices, sim_returns)


def plot_montecarlo(sim_prices, n_days, figsize=(10, 7)):
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
    ax.set_xlabel("Days")
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

    n_sims = sim_prices.shape[1]
    for i in range(n_sims):
        ax.plot(sim_prices[:, i], color='#2472C8', alpha=0.1)

    # Add the average simulation path
    avg_path = sim_prices.mean(axis=1)
    start_price = sim_prices[0, 0]
    ax.plot(avg_path, linewidth=4, color='#fd7e14', label='average')

    ax.set_title(
        f'Monte Carlo Simulation\n{jformat(n_days, 0)} days forecasted, {jformat(n_sims, 0)} simulations',
        color='white')

    # Add arrow annotation for the final average price
    final_price_avg = avg_path[-1]
    ax.annotate(
        f'Final average forecast: ${final_price_avg:,.0f}',
        color='#5fba7d',
        xy=(n_days - 1, (final_price_avg * 1.03)),
        xytext=(int(n_days * 0.3), final_price_avg * 1.1),
        arrowprops=dict(facecolor='green',
                        arrowstyle="->",
                        color='white',
                        lw=2),
        fontsize=14,
        bbox=dict(facecolor='black', alpha=0.5),
    )

    # Auto-scale the y-axis to show 90% of the final prices
    max_price = np.percentile(sim_prices[-1, :], 90)
    ax.set_ylim([start_price * 0.95, max_price])

    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format="png", transparent=True)

    # Embed the result in the html output.
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    return f"<img src='data:image/png;base64,{data}'/>"


def compute_monte_carlo_stats(sim_prices):
    stats = {}
    final_values = sim_prices[-1, :]

    stats['Average Final Value'] = np.mean(final_values)
    stats['Range of Final Value'] = [
        np.max(final_values), np.min(final_values)
    ]
    stats['90% Range of Final Values'] = [
        np.percentile(final_values, 95),
        np.percentile(final_values, 5)
    ]
    stats['95% Range of Final Values'] = [
        np.percentile(final_values, 97.5),
        np.percentile(final_values, 2.5)
    ]
    stats['Std Dev of Final Values'] = np.std(final_values)
    stats['1-Std Dev Range of Final Values'] = [
        np.mean(final_values) - np.std(final_values),
        np.mean(final_values) + np.std(final_values)
    ]

    initial_value = sim_prices[0, 0]

    stats['Prob Final Value Higher Than Initial Value'] = np.mean(
        final_values > initial_value)
    stats['Prob Final Value Dropping More Than 10%'] = np.mean(
        final_values < 0.9 * initial_value)
    stats['Prob Final Value Dropping More Than 25%'] = np.mean(
        final_values < 0.75 * initial_value)
    stats['Prob Final Value Dropping More Than 50%'] = np.mean(
        final_values < 0.5 * initial_value)

    stats['Prob Final Value Rising More Than 10%'] = np.mean(
        final_values > 1.1 * initial_value)
    stats['Prob Final Value Rising More Than 25%'] = np.mean(
        final_values > 1.25 * initial_value)
    stats['Prob Final Value Rising More Than 50%'] = np.mean(
        final_values > 1.5 * initial_value)

    return stats
