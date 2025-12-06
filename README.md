# Stock Simulation Profit Calculator

A browser-based stock backtesting sandbox that uses a simple “bias” strategy to buy dips and take profits on rallies. It fetches daily price data from Alpha Vantage, runs a grid search over a wide range of parameters, and visualizes both the real stock price and a simulated strategy value over time.

---
## Features

- **Single-stock simulation**
  - Enter a stock symbol *or* company name (e.g. “nvidia”, “apple inc” → `NVDA`, `AAPL`).
  - Automatically fetches full daily price history from Alpha Vantage.
  - Runs a bias-based trading strategy that:
    - Buys after sufficiently large drops over a lookback window.
    - Sells once a profit threshold is reached and a minimum hold time is satisfied.
  - Shows:
    - Final profit / loss in dollars.
    - Best thresholds found by grid search.
    - Last simulated action (BUY / SELL / HOLD) and amount.

- **Grid search optimizer**
  - Brute-force grid search across sell %, buy %, lookback days, risk multiplier, and minimum hold days.
  - Evaluates ~**90,000** parameter combinations per symbol.
  - Automatically picks the parameter set with the highest final wallet value.

- **Interactive chart**
  - Blue line: actual stock price.
  - Green line: **simulation value**, scaled by  
    `simulation_display_value = (total_value / START_WALLET) * stock_price`
  - Hover tooltip shows both real and simulated values in dollars (with 2 decimal places).
  - Scrollable, zoomable container (scrolling enabled, scrollbar hidden in UI).

- **Saved simulations**
  - Each run can be saved to localStorage.
  - Saved list shows:
    - Symbol
    - Latest profit (`+$123.45` / `-$67.89`)
    - Latest decision (e.g. `BUY 5`, `SELL 3`, or `HOLD`)
  - Rows are **sorted** so that:
    - Symbols with an actual action (BUY/SELL) appear at the top.
    - Within each group, highest profit comes first.
  - Click a saved row to re-run that symbol.
  - Per-symbol delete button + “clear all” button.

- **Portfolio sandbox (playground)**
  - Separate “sandbox” panel for combining multiple symbols.
  - Choose:
    - Starting cash.
    - A list of stocks and fixed share amounts to “hold”.
    - Optional start date filter.
  - Builds and displays:
    - **Manual portfolio curve:** value if you just held the specified shares over time.
    - **Optimized curve:** hypothetical “perfect timing” that always holds the single best-performing stock in your list at each point in time (an unrealistic but useful benchmark).

- **Smart API usage & caching**
  - Uses Alpha Vantage `TIME_SERIES_DAILY` endpoint.
  - Price data is cached per symbol in `localStorage` with:
    - Last fetch date.
    - A flag indicating whether it was fetched after the daily refresh cutoff.
  - If it’s a new trading day (or after the refresh time) the cache is bypassed and refreshed, helping avoid stale data while conserving your daily API call quota.

---

## Core Simulation Logic

**Strategy (per symbol):**

1. Start with `START_WALLET` cash and no shares.
2. For each new day:
   - **Sell logic:**
     - For every open lot:
       - Check how many days it’s been held.
       - Only consider selling lots that have been held at least `minHoldDays`.
       - Compute profit % from buy price to current price.
       - If profit % > `sellPctThresh`, sell the entire lot.
   - **Buy logic:**
     - Look back up to `maxLookbackDays` to find the **largest percent drop** from any previous price to today’s price.
     - If the largest drop is more negative than `-buyPctThresh`, trigger a BUY.
     - Determine number of shares to buy:
       - Compute `scaledDrop = abs(largest_drop_pct) * riskMultiplier`.
       - Buy 1 share per “step” up to `floor(scaledDrop)`, as long as there’s enough cash.
   - Update wallet and share holdings.
   - If tracking the equity curve, compute:
     - `total_value = wallet + shares * current_price`
     - Store `total_value` for that day.

3. At the end, return:
   - Final wallet + value of all shares.
   - Profit in dollars and percent.
   - Best parameter set used.
   - Last decision and amount.

**Simulation display line:**

- Internally, each day has a true `total_value`.
- On the chart, the green line is scaled to be visually comparable to price:

  ```txt
  simulation_display_value = (total_value / START_WALLET) * stock_price

v0.3.0 — 2025-12-05

Changed simulation value display formula to (total_value / START_WALLET) * stock_price for better visual comparison with price.

Improved chart hover tooltips to show both real price and simulation value in dollars with 2 decimal places.

Hid the scrollbar while keeping scroll behavior for the chart container.

v0.2.0 — 2025-12-04

Added portfolio sandbox with manual portfolio curve and an “optimized” best-performer curve.

Wired up portfolio inputs (start cash, per-symbol share amounts, optional start date).

Added portfolio chart with multiple lines.

v0.1.0 — 2025-12-03

Initial single-symbol bias trading simulator.

Implemented Alpha Vantage data fetching with local caching and daily refresh logic.

Added grid search over thresholds, risk multiplier, lookback, and min hold days.

Implemented saved simulations list with delete and clear-all actions.