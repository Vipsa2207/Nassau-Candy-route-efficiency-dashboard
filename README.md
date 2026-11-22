# Nassau Candy — Shipping Route Efficiency Dashboard

**Live app:** https://vipsa2207-nassau-candy-route-efficiency-dashboard-app-snxnaa.streamlit.app/

A Streamlit dashboard that compares 196 factory-to-state shipping routes on speed, consistency and delays, and shows whether ship mode or geography drives delivery time.

Project 3 of 4 · Built during my Data Analyst Internship at Unified Mentor (Jan–Jul 2026).

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?logo=pandas&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?logo=plotly&logoColor=white)
![PyDeck](https://img.shields.io/badge/PyDeck-2C3E50)

![Dashboard](docs/dashboard.png)

## The business question

Nassau Candy ships 15 products from 5 factories to customers in 59 US states and Canadian provinces. Which routes are slow or unreliable, and is the problem the route itself or the way orders are shipped?

## Key findings

- **Ship mode drives delivery time, not region.** Average lead time differs by **4.6 days** across ship modes (Same Day fastest, Standard Class slowest), but by only **0.24 days** across the four regions.
- **The same pattern shows in delays.** Under the app's delay measure, the delay rate varies by **30.9 percentage points** across ship modes (Standard Class 30.9%, First Class and Same Day 0%) and by only about **1 point** across regions (20.5%–21.5%).
- **Faster shipping is the lever, not rerouting.** Moving production to a different factory or region would barely change delivery time. Changing how orders ship would.

## How it works

1. **Clean the data** (`src/clean_data.py`). The raw ship dates are 2.5 to 4.5 years after the order dates, which is impossible. The script rebuilds a lead time from the remainder after dividing by 30 days (see Limitations), and links each product to its factory.
2. **Build features** (`src/feature_engineering.py`). Each order is flagged as delayed if its lead time is over 18 days (the 75th percentile). Each route (factory → state) gets an **efficiency score** from 0 to 100:
   - 50% speed (lower average lead time)
   - 30% consistency (lower spread of lead times)
   - 20% reliability (lower delay rate)
3. **The dashboard** (`app.py`) has filters for region, ship mode, order month and the delay threshold, and five sections:
   - **Overview:** route leaderboard, top and bottom 10 routes
   - **Route Map:** factory-to-state shipping flows on a map
   - **Ship Modes:** speed, delays and cost by ship mode
   - **Drill-Down:** one state's factories and monthly trend
   - **Findings:** auto-written insights from the filtered data

## How well it works

- **Small routes are excluded from rankings.** Only routes with 5 or more shipments are ranked (120 of 196). The 76 smaller routes would produce extreme scores from one or two orders.
- **Large routes score close together.** Among the 41 routes with 50+ shipments, scores range only from 47.6 to 63.9. That fits the main finding: route matters less than ship mode.
- **The ship-mode comparison holds up.** Ship modes are spread evenly across the date-error groups described below, so the differences between them are reliable even though the exact day counts are not.

## Limitations

- **Corrupted ship dates.** Raw lead times cluster at about 908, 1,273 and 1,639 days: the same short delivery plus 2, 3 or 4 extra years. The "remainder after 30 days" fix is an assumption, and it produces some unrealistic values, such as Same Day orders averaging 10 days.
- **Absolute delay rates are not reliable.** Every order flagged as delayed comes from the 4-extra-years group. The delay rate partly measures the date error, so only comparisons between groups should be used.
- **Thin data for two factories.** Sugar Shack has 33 shipments and The Other Factory 100, out of 10,194.
- **The efficiency score's weights were set by hand,** not tested against outcomes.

## Run it locally

```bash
git clone https://github.com/Vipsa2207/Nassau-Candy-route-efficiency-dashboard.git
cd Nassau-Candy-route-efficiency-dashboard
pip install -r requirements.txt
streamlit run app.py
```

To rebuild the data from the raw file:

```bash
python src/clean_data.py
python src/feature_engineering.py
```

## Project files

| File | What it is |
|---|---|
| `app.py` | The Streamlit dashboard |
| `src/clean_data.py` | Fixes dates, links products to factories |
| `src/feature_engineering.py` | Delay flag and route efficiency score |
| `src/geo_lookup.py` | State and province coordinates for the map |
| `data/` | Raw, cleaned and feature data, plus the route summary |

## Research paper

I authored a research paper on this project (JETIR paper ID 584017, accepted, not published). A revised version will be added to this repository.

## How I built it

I used AI to help write the Python code. I framed the business question, worked through the ship-date problem, checked the outputs against the data, and wrote the findings.

## Author

**Vipsa Patel** — Data Analyst Intern, Unified Mentor · [LinkedIn](https://www.linkedin.com/in/vipsapatel)
