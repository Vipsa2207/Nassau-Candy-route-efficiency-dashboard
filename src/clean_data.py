"""
Nassau Candy Distributor - Data Cleaning & Preparation
Step 2 of the Factory-to-Customer Shipping Route Efficiency Analysis
"""

import pandas as pd

RAW_PATH = "data/nassau_candy_raw.csv"
CLEAN_PATH = "data/nassau_candy_cleaned.csv"

# 1. LOAD
df = pd.read_csv(RAW_PATH)
print(f"Loaded {len(df)} rows, {df['Order ID'].nunique()} unique orders")

# 2. PARSE DATES (stored as DD-MM-YYYY)
df["Order Date"] = pd.to_datetime(df["Order Date"], format="%d-%m-%Y")
df["Ship Date"] = pd.to_datetime(df["Ship Date"], format="%d-%m-%Y")

# 3. FIX THE SHIP DATE ANOMALY
# Raw (Ship Date - Order Date) clusters at about 908, 1,273 and 1,639 days:
# the same short delivery plus 2, 3 or 4 whole extra years. The extra years
# depend on the order date (2024 orders: +2 or +3 years; 2025 orders: +3 or +4),
# so they are an error, not shipping speed.
# Fix: assign each order to its year-offset group, then measure it against the
# median of that group. The result is "days faster (-) or slower (+) than a
# typical order". Centring each group on its own median also absorbs the
# 2028 leap day. The true number of days in transit cannot be recovered.
# (An earlier version used Raw % 30; that mixed the year offset into lead
# time, so 2025 orders looked about 6 days slower than 2024 orders.)
df["Raw Lead Time (days)"] = (df["Ship Date"] - df["Order Date"]).dt.days
df["Year Offset Group"] = ((df["Raw Lead Time (days)"] - 908) / 365.25).round().astype(int)
group_median = df.groupby("Year Offset Group")["Raw Lead Time (days)"].transform("median")
df["Shipping Lead Time (Days)"] = df["Raw Lead Time (days)"] - group_median

print("\nYear-offset groups (rows, median raw days):")
print(df.groupby("Year Offset Group")["Raw Lead Time (days)"].agg(["size", "median"]))
print("\nRelative lead time by Ship Mode (should rise from Same Day to Standard):")
print(df.groupby("Ship Mode")["Shipping Lead Time (Days)"].mean().sort_values().round(2))

# 4. VALIDATE / DROP IMPOSSIBLE ROWS
before = len(df)
df = df.dropna(subset=["Order Date", "Ship Date", "Sales", "Units"])
print(f"\nDropped {before - len(df)} invalid rows")

# 5. STANDARDIZE GEOGRAPHIC FIELDS
for col in ["City", "State/Province", "Country/Region", "Region"]:
    df[col] = df[col].str.strip().str.title()
df["Product Name"] = df["Product Name"].str.strip()

# 6. ATTACH FACTORY INFO (needed for route + map analysis)
FACTORY_COORDS = {
    "Lot's O' Nuts":     (32.881893, -111.768036),
    "Wicked Choccy's":   (32.076176,  -81.088371),
    "Sugar Shack":       (48.119140,  -96.181150),
    "Secret Factory":    (41.446333,  -90.565487),
    "The Other Factory": (35.117500,  -89.971107),
}

PRODUCT_TO_FACTORY = {
    "Wonka Bar - Nutty Crunch Surprise": "Lot's O' Nuts",
    "Wonka Bar - Fudge Mallows": "Lot's O' Nuts",
    "Wonka Bar -Scrumdiddlyumptious": "Lot's O' Nuts",
    "Wonka Bar - Milk Chocolate": "Wicked Choccy's",
    "Wonka Bar - Triple Dazzle Caramel": "Wicked Choccy's",
    "Laffy Taffy": "Sugar Shack",
    "SweeTARTS": "Sugar Shack",
    "Nerds": "Sugar Shack",
    "Fun Dip": "Sugar Shack",
    "Fizzy Lifting Drinks": "Sugar Shack",
    "Everlasting Gobstopper": "Secret Factory",
    "Hair Toffee": "The Other Factory",
    "Lickable Wallpaper": "Secret Factory",
    "Wonka Gum": "Secret Factory",
    "Kazookles": "The Other Factory",
}

df["Factory"] = df["Product Name"].map(PRODUCT_TO_FACTORY)
df["Factory Lat"] = df["Factory"].map(lambda f: FACTORY_COORDS[f][0])
df["Factory Lon"] = df["Factory"].map(lambda f: FACTORY_COORDS[f][1])

unmapped = df["Factory"].isna().sum()
if unmapped:
    print(f"WARNING: {unmapped} rows could not be mapped to a factory")
else:
    print("\nAll products successfully mapped to a factory")

# 7. ROUTE DEFINITION
df["Route"] = df["Factory"] + " -> " + df["State/Province"]

# 8. SAVE
df.to_csv(CLEAN_PATH, index=False)
print(f"\nSaved cleaned data to {CLEAN_PATH} ({len(df)} rows, {df.shape[1]} columns)")