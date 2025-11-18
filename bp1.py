
import requests
import datetime as dt
from statistics import mean

API_KEY = "BT8UUAJIJ09B1IQF"  # <-- put your Alpha Vantage key here


# ============================
#  DATA FETCHING
# ============================

def fetch_daily_series(symbol: str, api_key: str):
    """
    Fetch full daily close prices for a symbol from Alpha Vantage.
    Returns a list of (date, close) sorted from oldest -> newest.
    """
    url = (
        "https://www.alphavantage.co/query"
        "?function=TIME_SERIES_DAILY"
        f"&symbol={symbol}"
        "&outputsize=full"
        f"&apikey={api_key}"
    )
    resp = requests.get(url)
    data = resp.json()

    time_series = data.get("Time Series (Daily)")
    if time_series is None:
        raise RuntimeError(f"Unexpected response from Alpha Vantage: {data}")

    date_close_pairs = []
    for date_str, daily in time_series.items():
        date_obj = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
        close_price = float(daily["4. close"])
        date_close_pairs.append((date_obj, close_price))

    # sort from oldest -> newest
    date_close_pairs.sort(key=lambda x: x[0])
    return date_close_pairs


# ============================
#  BIAS / MULTIPLIER LOGIC
# ============================

def sign(x: float) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def compute_bias_and_decision(
    symbol: str,
    api_key: str,
    months_back: int = 6,
    base_shares: int = 5,
    threshold_pct: float = 0.05,  # 5% up/down for base SELL/BUY
):
    """
    - Fetches price history for `symbol`
    - Looks at the last `months_back` months
    - Computes bias based on daily moves & time distance
    - Uses that bias to scale base buy/sell shares.

    Returns a dict with:
      action: 'BUY' | 'SELL' | 'HOLD'
      final_shares: int
      bias_net: float
      bias_multiplier_buy: float
      bias_multiplier_sell: float
      today_date: date
      today_price: float
    """
    date_close_pairs = fetch_daily_series(symbol, api_key)
    if not date_close_pairs:
        raise ValueError("No price data returned.")

    # "Today" = latest trading day in the series
    today_date, today_price = date_close_pairs[-1]

    # Approximate 6 months as 182 days
    lookback_days = months_back * 30  # or 182 fixed if you prefer
    lookback_start_date = today_date - dt.timedelta(days=lookback_days)

    # Filter window: dates between lookback_start_date and today_date (inclusive)
    window = [(d, p) for (d, p) in date_close_pairs if lookback_start_date <= d <= today_date]
    if len(window) < 2:
        raise ValueError("Not enough data in the 6-month window.")

    # Price on "today" (already have) – used for pct_delta_from_run
    price_today = today_price

    bias_up = 0.0
    bias_down = 0.0
    bias_net = 0.0

    # We'll use these for optional debugging info
    pct_delta_from_run_list = []
    pct_delta_from_prev_list = []

    for i, (current_date, current_price) in enumerate(window):
        days_from_run = (today_date - current_date).days  # 0 for today, >0 for past

        # Percent change vs run-day price
        pct_delta_from_run = (current_price - price_today) / price_today
        pct_delta_from_run_list.append(pct_delta_from_run)

        # Percent change vs previous trading day in window
        if i == 0:
            pct_delta_from_prev = 0.0
        else:
            prev_price = window[i - 1][1]
            pct_delta_from_prev = (current_price - prev_price) / prev_price
        pct_delta_from_prev_list.append(pct_delta_from_prev)

        direction = sign(pct_delta_from_prev)

        # Time weight: recent days matter more (1.0 at today, ~0 at 6 months)
        # Clamp at min 0.1 so old days still have a tiny say
        time_weight = max(0.1, 1.0 - days_from_run / float(lookback_days))

        # Magnitude weight: bigger daily moves matter more
        # Scale so ±5% move corresponds to weight ~1.0
        magnitude_weight = min(1.0, abs(pct_delta_from_prev) / 0.05)

        bias_increment = direction * time_weight * magnitude_weight

        if bias_increment > 0:
            bias_up += bias_increment
        elif bias_increment < 0:
            bias_down += bias_increment

        bias_net += bias_increment

    window_len = len(window)
    if window_len == 0:
        raise ValueError("Empty analysis window.")

    # Normalize net bias to [-1, 1] range
    raw_bias = bias_net / window_len
    raw_bias = max(-1.0, min(1.0, raw_bias))

    # Positive bias => trend up => more inclined to SELL, less to BUY
    # Negative bias => trend down => more inclined to BUY, less to SELL
    sell_scale = 2.0  # up to +200% of base
    buy_scale = 2.0

    bias_multiplier_sell = 1.0 + max(0.0, raw_bias) * sell_scale
    bias_multiplier_buy = 1.0 + max(0.0, -raw_bias) * buy_scale

    # Base decision based on price vs earliest date in 6-month window
    start_date, start_price = window[0]
    pct_change_vs_start = (today_price - start_price) / start_price

    if pct_change_vs_start >= threshold_pct:
        base_action = "SELL"
    elif pct_change_vs_start <= -threshold_pct:
        base_action = "BUY"
    else:
        base_action = "HOLD"

    if base_action == "SELL":
        final_shares = int(round(base_shares * bias_multiplier_sell))
    elif base_action == "BUY":
        final_shares = int(round(base_shares * bias_multiplier_buy))
    else:
        final_shares = 0

    return {
        "symbol": symbol,
        "action": base_action,
        "final_shares": final_shares,
        "base_shares": base_shares,
        "threshold_pct": threshold_pct,
        "bias_up": bias_up,
        "bias_down": bias_down,
        "bias_net": bias_net,
        "raw_bias": raw_bias,
        "bias_multiplier_buy": bias_multiplier_buy,
        "bias_multiplier_sell": bias_multiplier_sell,
        "today_date": today_date,
        "today_price": today_price,
        "start_date": start_date,
        "start_price": start_price,
        "pct_change_vs_start": pct_change_vs_start,
    }


# ============================
#  MAIN
# ============================

if __name__ == "__main__":
    symbol = input("Enter stock symbol (e.g. NVDA, TSLA): ").strip().upper()
    if not symbol:
        symbol = "NVDA"

    result = compute_bias_and_decision(
        symbol=symbol,
        api_key=API_KEY,
        months_back=6,
        base_shares=5,
        threshold_pct=0.05,  # 5% vs 6 months ago
    )

    print("\n=== 6-Month Bias Decision ===")
    print(f"Symbol:          {result['symbol']}")
    print(f"Today (run date): {result['today_date']} @ {result['today_price']:.2f}")
    print(f"Start of window: {result['start_date']} @ {result['start_price']:.2f}")
    print(f"6M change:       {result['pct_change_vs_start']*100:.2f}%")

    print(f"\nBias net:        {result['bias_net']:.4f}")
    print(f"Raw bias [-1,1]: {result['raw_bias']:.4f}")
    print(f"Buy multiplier:  {result['bias_multiplier_buy']:.2f}")
    print(f"Sell multiplier: {result['bias_multiplier_sell']:.2f}")

    print(f"\nBase shares:     {result['base_shares']}")
    print(f"Threshold:       {result['threshold_pct']*100:.2f}% vs 6M ago")
    print(f"Action:          {result['action']}")
    print(f"Final shares:    {result['final_shares']}")
