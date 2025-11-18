# from helper import Helper
#
# Stocks = Helper()



import csv
import datetime as dt


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


def price_delta(stock_data, date1, date2):
    price_map = {d: p for d, p in stock_data}
    if date1 not in price_map or date2 not in price_map:
        raise ValueError("Date not found in data")
    price1 = price_map[date1]
    price2 = price_map[date2]
    delta_raw = price2 - price1
    delta_percent = (delta_raw / price1) if price1 != 0 else 0
    return int(price1 * 100) / 100, int(price2 * 100) / 100, int(delta_raw * 100) / 100, int(delta_percent * 10000) / 100


def best_worst_percent_change(stock_data, start_date, end_date):
    window = [(d, p) for d, p in stock_data if start_date <= d <= end_date]
    if len(window) < 2:
        return 0.0
    bias_points = 0.0
    for i in range(1, len(window)):
        _, prev_price = window[i - 1]
        _, cur_price = window[i]
        if prev_price == 0:
            continue
        delta_percent = (cur_price - prev_price) / prev_price * 100
        bias_points += delta_percent
    return bias_points




stock_data = load_csv("NVDA.csv")
start_date = dt.date(2024, 1, 1)
end_date = dt.date(2024, 6, 30)

bias = best_worst_percent_change(stock_data, start_date, end_date)
print("Bias points:", bias)
