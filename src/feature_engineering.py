"""
Nassau Candy Distributor - Feature Engineering
Step 3: builds order-level features + route-level Efficiency Score
"""

import pandas as pd

CLEAN_PATH = "data/nassau_candy_cleaned.csv"
ORDERS_OUT = "data/nassau_candy_features.csv"
ROUTES_OUT = "data/route_summary.csv"

DELAY_THRESHOLD_DAYS = 18  # default = 75th percentile of lead time distribution
                           # (Streamlit app lets users override this with a slider)

df = pd.read_csv(CLEAN_PATH)
df["Order Date"] = pd.to_datetime(df["Order Date"])
df["Ship Date"] = pd.to_datetime(df["Ship Date"])

# ---------------------------------------------------------------
# ORDER-LEVEL FEATURES
# ---------------------------------------------------------------
df["Order Month"] = df["Order Date"].dt.month_name()
df["Order Weekday"] = df["Order Date"].dt.day_name()
df["Is Delayed"] = (df["Shipping Lead Time (Days)"] > DELAY_THRESHOLD_DAYS).astype(int)
df["Factory -> Region"] = df["Factory"] + " -> " + df["Region"]

df.to_csv(ORDERS_OUT, index=False)
print(f"Saved order-level features to {ORDERS_OUT} ({len(df)} rows)")

# ---------------------------------------------------------------
# ROUTE-LEVEL AGGREGATION
# Route = Factory -> Customer State
# ---------------------------------------------------------------
routes = df.groupby(["Factory", "State/Province", "Region", "Route"]).agg(
    Total_Shipments=("Row ID", "count"),
    Avg_Lead_Time=("Shipping Lead Time (Days)", "mean"),
    Lead_Time_Std=("Shipping Lead Time (Days)", "std"),
    Delay_Rate=("Is Delayed", "mean"),
    Total_Sales=("Sales", "sum"),
    Total_Units=("Units", "sum"),
    Total_Gross_Profit=("Gross Profit", "sum"),
).reset_index()

routes["Lead_Time_Std"] = routes["Lead_Time_Std"].fillna(0)

# ---------------------------------------------------------------
# ROUTE EFFICIENCY SCORE (0-100, higher = better)
# 50% Speed (lower avg lead time is better)
# 30% Consistency (lower lead time variability is better)
# 20% Reliability (lower delay rate is better)
# ---------------------------------------------------------------
def scale_inverse(series):
    lo, hi = series.min(), series.max()
    if hi == lo:
        return pd.Series(100, index=series.index)
    return 100 * (1 - (series - lo) / (hi - lo))

routes["Speed_Score"] = scale_inverse(routes["Avg_Lead_Time"])
routes["Consistency_Score"] = scale_inverse(routes["Lead_Time_Std"])
routes["Reliability_Score"] = scale_inverse(routes["Delay_Rate"])

routes["Route_Efficiency_Score"] = (
    0.5 * routes["Speed_Score"]
    + 0.3 * routes["Consistency_Score"]
    + 0.2 * routes["Reliability_Score"]
).round(1)

routes = routes.sort_values("Route_Efficiency_Score", ascending=False).reset_index(drop=True)
routes["Efficiency Rank"] = routes.index + 1

routes.to_csv(ROUTES_OUT, index=False)
print(f"Saved route-level summary to {ROUTES_OUT} ({len(routes)} unique routes)")

print("\nTOP 5 MOST EFFICIENT ROUTES:")
print(routes[["Route", "Route_Efficiency_Score", "Avg_Lead_Time", "Total_Shipments"]].head(5).to_string(index=False))

print("\nBOTTOM 5 LEAST EFFICIENT ROUTES:")
print(routes[["Route", "Route_Efficiency_Score", "Avg_Lead_Time", "Total_Shipments"]].tail(5).to_string(index=False))