# from helper import Helper
#
# Stocks = Helper()

#
# import csv
# import datetime as dt
#
#
# def load_csv(filename):
#     stock_data = []
#     with open(filename, newline="") as f:
#         reader = csv.DictReader(f)
#         for row in reader:
#             date_str = row["Date"]
#             close_str = row["Close/Last"]
#             close_str = close_str.replace("$", "").replace(",", "").strip()
#             date_obj = dt.datetime.strptime(date_str, "%m/%d/%Y").date()
#             close_price = float(close_str)
#             stock_data.append((date_obj, close_price))
#     stock_data.sort(key=lambda x: x[0])
#     return stock_data
#
#
# def price_delta(stock_data, date1, date2):
#     price_map = {d: p for d, p in stock_data}
#     if date1 not in price_map or date2 not in price_map:
#         raise ValueError("Date not found in data")
#     price1 = price_map[date1]
#     price2 = price_map[date2]
#     delta_raw = price2 - price1
#     delta_percent = (delta_raw / price1) if price1 != 0 else 0
#     return int(price1 * 100) / 100, int(price2 * 100) / 100, int(delta_raw * 100) / 100, int(delta_percent * 10000) / 100
#
#
# # percent_bias = [[i, 1] for i in range(1, 100)]
# data = load_csv("NVDA.csv")
# wallet = 0
# shares = [[180, 100]]
# print(shares[0][0] * shares[0][1])
#
# def clamp(n, min_val, max_val):
#     return max(min(n, max_val), min_val)
#
# for i, (date, price) in enumerate(data):
#     if i < len(data) - 30 or i > len(data) - 1:
#         continue
#     # print(i)
#     d2 = date - dt.timedelta(days=1)
#     try:
#         p1, p2, diff, pct = price_delta(data, date, d2)
#     except ValueError:
#         continue
#     decision = None
#     if pct < -1:
#         print(pct, wallet, date)
#         shares_amount = 0
#         for x in range(1, int(abs(pct)) + 1):
#             if wallet >= p1 * x:
#                 shares_amount += 1
#         if shares_amount > 0:
#             wallet -= p1 * shares_amount
#             decision = "Buy " + str(shares_amount) + " shares at $" + str(p1)
#             shares.append([p1, shares_amount])
#     elif pct > 1:
#         shares_sold = 0
#         price_at = 0
#         remaining_shares = abs(int(pct))
#         for x in range(0, len(shares)):
#             shares_sold += clamp(shares[x][1], 0, remaining_shares)
#             price_at += p1 * clamp(shares[x][1], 0, remaining_shares)
#             wallet += p1 * clamp(shares[x][1], 0, remaining_shares)
#             shares[x][1] -= clamp(shares[x][1], 0, remaining_shares)
#             remaining_shares -= clamp(shares[x][1], 0, remaining_shares)
#             if remaining_shares == 0:
#                 break
#         new_shares = []
#         for x in range(0, len(shares)):
#             if shares[x][1] != 0:
#                 new_shares.append(shares[x])
#         shares = new_shares
#         decision = "Sell " + str(shares_sold) + " shares at $" + str(price_at)
#     if decision != None:
#         print("$" + str(int(wallet * 100) / 100), "|", decision, "|", date, "|", shares)
#
# for i in shares:
#     wallet += i[0] * i[1]
# print("============")
# print(int(wallet * 100) / 100)



















import csv
import datetime as dt


# =========================
# 1. LOAD DATA
# =========================

def load_csv(filename):
    stock_data = []
    with open(filename, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_str = row["Date"]
            close_str = row["Close/Last"]
            close_str = close_str.replace("$", "").replace(",", "").strip()
            date_obj = dt.datetime.strptime(date_str, "%m/%d/%Y").date()
            close_price = float(close_str)
            stock_data.append((date_obj, close_price))
    stock_data.sort(key=lambda x: x[0])
    return stock_data


# =========================
# 2. HELPERS
# =========================

def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def compute_daily_pct(data):
    """
    data: list[(date, price)] sorted
    returns list of daily % moves aligned with data indices
    daily_pct[i] is % move from i-1 -> i (0 for i=0)
    """
    daily_pct = [0.0] * len(data)
    for i in range(1, len(data)):
        prev = data[i - 1][1]
        cur = data[i][1]
        if prev != 0:
            daily_pct[i] = (cur - prev) / prev * 100.0
        else:
            daily_pct[i] = 0.0
    return daily_pct


def calc_bias(daily_pct, i, lookback_days):
    """
    Volatility-based bias at index i:
      - Use last `lookback_days` daily pct moves (trading days)
      - bias ~ 1 when calm
      - bias > 1 when volatile
    """
    start = max(1, i - lookback_days)  # skip index 0 (no move)
    window = daily_pct[start : i + 1]
    if not window:
        return 1.0
    avg_abs = sum(abs(x) for x in window) / len(window)  # in %
    avg_frac = avg_abs / 100.0                           # -> 0.x

    bias = 1.0 + avg_frac
    return clamp(bias, 0.5, 2.0)


# =========================
# 3. SINGLE BACKTEST WITH BEST PARAMS
# =========================

def run_strategy(data, daysAmount, pct_thresh=1.0, lookback_days=30,
                 starting_cash=1000.0, verbose=True):
    prices = [p for _, p in data]
    daily_pct = compute_daily_pct(data)

    cash = starting_cash
    shares = 0

    start_index = max(1, len(data) - daysAmount)

    for i in range(start_index, len(data)):
        date, price = data[i]

        # need enough history for bias
        if i <= lookback_days:
            continue

        dp = daily_pct[i]  # today's % move vs yesterday
        bias = calc_bias(daily_pct, i, lookback_days)

        decision = None

        # ===== BUY RULE =====
        if dp <= -pct_thresh:
            # drop bigger than threshold -> buy
            drop_factor = abs(dp) / pct_thresh      # 1.0 at exactly threshold
            invest_fraction = clamp(0.05 * drop_factor * bias, 0.0, 0.6)
            to_invest = cash * invest_fraction
            qty = int(to_invest // price)
            if qty > 0:
                cash -= qty * price
                shares += qty
                decision = f"BUY {qty} @ {price:.2f} (dp={dp:.2f}%, bias={bias:.2f})"

        # ===== SELL RULE =====
        elif dp >= pct_thresh and shares > 0:
            rise_factor = dp / pct_thresh
            sell_fraction = clamp(0.05 * rise_factor * bias, 0.0, 0.6)
            qty = int(shares * sell_fraction)
            if qty > 0:
                cash += qty * price
                shares -= qty
                decision = f"SELL {qty} @ {price:.2f} (dp={dp:.2f}%, bias={bias:.2f})"

        if verbose and decision:
            print(f"{date} | price={price:.2f} | cash={cash:.2f} | shares={shares} | {decision}")

    final_value = cash + shares * data[-1][1]
    return final_value, cash, shares


# =========================
# 4. RUN
# =========================

if __name__ == "__main__":
    data = load_csv("AAPL.csv")

    STARTING_CASH = 1000.0
    BEST_THRESH = 1.0     # 1%
    BEST_WINDOW = 30      # 30 trading days

    final_value, final_cash, final_shares = run_strategy(
        data,
        daysAmount=360,
        pct_thresh=BEST_THRESH,
        lookback_days=BEST_WINDOW,
        starting_cash=STARTING_CASH,
        verbose=False,          # set False if you don't want per-trade logs
    )

    print("\n============ SUMMARY ============")
    print(f"Final cash:     ${final_cash:,.2f}")
    print(f"Total profit:   ${final_value - STARTING_CASH:,.2f}")
    print(f"Total return:   {(final_value / STARTING_CASH - 1) * 100:.2f}%")
