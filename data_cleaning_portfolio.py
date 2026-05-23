"""
=============================================================
  E-COMMERCE DATA CLEANING — PORTFOLIO PROJECT
  Dataset: East Africa Orders (5,115 rows × 21 columns)
=============================================================
USE CASES COVERED
  1.  Load & first look
  2.  Fix column names (whitespace, mixed casing, special chars)
  3.  Remove duplicate orders
  4.  Standardise categorical columns
       a. Order Status   (17 raw → 6 canonical)
       b. Payment Method (17 raw → 4 canonical)
       c. Product Category (24 raw → 7 canonical)
       d. City/Town      (spaces, abbreviations)
  5.  Parse & validate dates  (5 different formats → ISO)
  6.  Handle missing values   (strategy per column)
  7.  Fix data-type issues    (phone as float → string)
  8.  Detect & cap age outliers
  9.  Validate email addresses
 10.  Normalise Total Amount across currencies → KES
 11.  Export clean dataset + cleaning report
=============================================================
"""

import re                    # built-in: regular expressions (used for email validation)
import pandas as pd          # data manipulation — the core library for this project
import numpy as np           # numerical operations and NaN handling
from datetime import datetime  # built-in: for parsing date strings into date objects

# ── Helper: pretty section header printed to terminal ─────────────────────────
DIVIDER = "\n" + "=" * 65 + "\n"

def section(title):
    """Print a visible section header so the terminal output is easy to follow."""
    print(f"{DIVIDER}  {title}{DIVIDER}")


# =============================================================================
# 1. LOAD & FIRST LOOK
# =============================================================================
section("1. LOAD & FIRST LOOK")

RAW_PATH   = "messy_data__1_.csv"
CLEAN_PATH = "orders_clean.csv"

# dtype=str tells pandas to read EVERY column as a plain string.
# Without this, pandas would guess types — and would turn phone numbers
# like 254797291993 into floats (2.547e+11), permanently destroying
# the leading digits. We cast to proper types manually later (Step 7).
df = pd.read_csv(RAW_PATH, dtype=str)

print(f"Shape : {df.shape}")
print(f"\nColumn names (raw):\n{list(df.columns)}")
print(f"\nMissing values per column:\n{df.isnull().sum()}")


# =============================================================================
# 2. FIX COLUMN NAMES
# =============================================================================
section("2. FIX COLUMN NAMES")

# ── Step 2a: Auto-clean with a method chain ───────────────────────────────────
# .str.strip()        → removes leading and trailing whitespace
#                       e.g. ' Order ID ' → 'Order ID'
# .str.lower()        → converts to lowercase
#                       e.g. 'CUSTOMER__Name' → 'customer__name'
# .str.replace(...)   → replaces spaces, slashes, dashes, brackets, %, ? with _
#                       e.g. 'Age (yrs)' → 'age__yrs_'
# second .replace     → collapses multiple consecutive underscores into one
#                       e.g. 'age__yrs_' → 'age_yrs_'
# .str.strip("_")     → removes leading/trailing underscores left over
#                       e.g. 'age_yrs_' → 'age_yrs'
df.columns = (
    df.columns
      .str.strip()
      .str.lower()
      .str.replace(r"[\s/\-\.\(\)\?%]+", "_", regex=True)
      .str.replace(r"_+", "_", regex=True)
      .str.strip("_")
)

# ── Step 2b: Rename to short, readable snake_case names ───────────────────────
# After auto-clean some names are still verbose (e.g. 'unit_price_kes_usd_eur').
# We use an explicit rename dictionary for clarity.
# The dict comprehension at the end only applies keys that actually exist
# in the dataframe — avoids KeyError if a column was already renamed.
RENAME = {
    "e_mail_address":          "email",
    "phone_no":                "phone",
    "city_town":               "city",
    "age_yrs":                 "age",
    "product_cat":             "category",
    "unit_price_kes_usd_eur":  "unit_price",
    "discount":                "discount_pct",
    "curr":                    "currency",
    "review_rating_1_5":       "review_rating",
    "full_address_street_zip": "address",
}

df.rename(columns={k: v for k, v in RENAME.items() if k in df.columns}, inplace=True)
print("Cleaned column names:", list(df.columns))


# =============================================================================
# 3. REMOVE DUPLICATE ORDERS
# =============================================================================
section("3. REMOVE DUPLICATE ORDERS")

before = len(df)

# drop_duplicates checks if a value in 'order_id' has appeared before.
# keep='first' → retains the first occurrence and removes all later ones.
# inplace=True → modifies df directly instead of returning a new dataframe.
df.drop_duplicates(subset="order_id", keep="first", inplace=True)
df.reset_index(drop=True, inplace=True)   # reindex from 0 after row removal
print(f"Removed {before - len(df)} duplicate rows → {len(df)} remain")


# =============================================================================
# 4. STANDARDISE CATEGORICAL COLUMNS
# =============================================================================
section("4. STANDARDISE CATEGORICAL COLUMNS")

# ── The make_mapper factory function ─────────────────────────────────────────
# This function is a "factory" — it takes a dictionary and RETURNS a new function.
#
# The dictionary format is:
#   { "canonical_value": ["variant1", "variant2", "variant3"], ... }
#
# Inside make_mapper we build a REVERSE lookup dictionary using a dict
# comprehension. The reverse dict maps every variant to its canonical value:
#   { "variant1": "canonical_value", "variant2": "canonical_value", ... }
#
# The inner `mapper` function:
#   1. Returns NaN if the value is missing (pd.isna check)
#   2. Strips whitespace from the value (.strip())
#   3. Looks up the stripped value in the reverse dict
#   4. Returns "other" if the value isn't found (safe fallback)
#
# Example:
#   make_mapper({"pending": ["Pending", "PENDING", "pending"]})
#   → reverse = {"Pending": "pending", "PENDING": "pending", "pending": "pending"}
#   → mapper("PENDING") returns "pending"
#   → mapper("shipped") returns "other"  ← not in this particular map
#   → mapper(None)      returns NaN

def make_mapper(mapping_dict):
    """
    Factory that builds a value-standardisation function from a variant map.

    Parameters
    ----------
    mapping_dict : dict
        Keys are canonical (target) values.
        Values are lists of raw strings that should map to that canonical value.

    Returns
    -------
    function
        A function that accepts a single cell value and returns
        the canonical string, NaN, or "other".
    """
    # Build reverse lookup: every variant → its canonical key
    reverse = {variant: canonical
               for canonical, variants in mapping_dict.items()
               for variant in variants}

    def mapper(val):
        if pd.isna(val):
            return np.nan                          # preserve missing values
        return reverse.get(str(val).strip(), "other")  # strip then look up

    return mapper   # return the inner function so it can be used with .apply()


# ── 4a. Order Status ──────────────────────────────────────────────────────────
# Raw data had 17 variants: 'Pending', 'PENDING', 'pending', 'Complete', etc.
# We collapse them into 6 clean canonical values.
STATUS_MAP = {
    "pending":    ["pending", "Pending", "PENDING"],
    "shipped":    ["shipped", "Shipped"],
    "delivered":  ["delivered", "Delivered", "DELIVERED", "Complete", "complete"],
    "cancelled":  ["cancelled", "Cancelled", "CANCELLED", "Canceled"],
    "returned":   ["returned", "Returned", "Return", "return"],
    "in transit": ["In Transit", "in transit"],
}

# .apply(func) calls func once for every cell in the column
# make_mapper(STATUS_MAP) returns the mapper function, which apply then uses
df["order_status"] = df["order_status"].apply(make_mapper(STATUS_MAP))
print("Order Status:", sorted(df["order_status"].dropna().unique()))


# ── 4b. Payment Method ────────────────────────────────────────────────────────
# Raw data had 17 variants: 'CASH', 'cash', 'M-PESA', 'Mpesa', 'mobile money', etc.
PAYMENT_MAP = {
    "cash":          ["cash", "CASH", "Cash"],
    "mpesa":         ["M-PESA", "M-Pesa", "Mpesa", "mpesa", "mobile money", "Mobile Money"],
    "card":          ["card", "Card", "CARD", "Debit Card", "Credit card", "Credit Card"],
    "bank transfer": ["Bank", "bank", "Bank Transfer", "bank transfer", "BANK TRANSFER"],
}

df["payment_method"] = df["payment_method"].apply(make_mapper(PAYMENT_MAP))
print("Payment Method:", sorted(df["payment_method"].dropna().unique()))


# ── 4c. Product Category ──────────────────────────────────────────────────────
# Raw data had 24 variants including typos: 'Electrnics', 'Beauti', 'Fashn', 'ELEC'
CATEGORY_MAP = {
    "beauty":      ["beauty", "Beauty", "Beauti"],
    "sports":      ["sports", "Sports", "Sport"],
    "books":       ["books", "Books", "Book"],
    "home":        ["HOME", "Home & Kitchen", "Home/Kitchen", "home and kitchen", "home"],
    "clothing":    ["Clothing", "clothing", "Fashion", "fashion", "Fashn"],
    "electronics": ["Electronics", "electronics", "Electrnics", "ELEC"],
    "groceries":   ["groceries", "Groceries", "Grocery"],
}

df["category"] = df["category"].apply(make_mapper(CATEGORY_MAP))
print("Category:", sorted(df["category"].dropna().unique()))


# ── 4d. City / Town ───────────────────────────────────────────────────────────
# Cities had: leading spaces (' Thika'), abbreviations ('NBO', 'KSM', 'KLA'),
# and typos ('Nairobii'). We use a slightly different approach here because
# we also want to preserve unknown cities (just lowercased), not label them "other".
CITY_MAP = {
    "nairobi":       ["nairobi", "Nairobi", "NBO", "Nairobii"],
    "mombasa":       ["mombasa", "Mombasa"],
    "kisumu":        ["kisumu", "Kisumu", "KSM"],
    "kampala":       ["kampala", "Kampala", "KLA"],
    "machakos":      ["machakos", "Machakos"],
    "thika":         ["thika", "Thika", " Thika"],
    "dar es salaam": ["dar es salaam", "Dar es Salaam", "Dar Es Salaam"],
    "nakuru":        ["nakuru", "Nakuru"],
    "eldoret":       ["eldoret", "Eldoret"],
}

def map_city(val):
    """
    Normalise city names.
    Known variants → canonical lowercase name.
    Unknown values → lowercased and stripped (not discarded as 'other').
    Missing values → NaN preserved.
    """
    if pd.isna(val):
        return np.nan
    v = str(val).strip()
    for canonical, variants in CITY_MAP.items():
        if v in variants:
            return canonical
    return v.lower()   # unknown city: keep it, just normalise the casing

df["city"] = df["city"].apply(map_city)
print(f"\nTop 8 cities:\n{df['city'].value_counts().head(8)}")


# =============================================================================
# 5. PARSE & VALIDATE DATES
# =============================================================================
section("5. PARSE & VALIDATE DATES")

# The dataset contains at least 5 different date formats in the same column:
#   21/03/2025  → day/month/year  (%d/%m/%Y)
#   2024-05-13  → ISO 8601        (%Y-%m-%d)
#   10-08-2024  → day-month-year  (%d-%m-%Y)
#   02-26-2023  → month-day-year  (%m-%d-%Y)  ← US format
#   20-Aug-2024 → day-abbr-year   (%d-%b-%Y)
#
# pd.to_datetime(infer_datetime_format=True) can silently mis-parse ambiguous
# dates — e.g. "10-08-2024" could be Aug 10 or Oct 8. We try each format
# explicitly and in order of specificity, which is deterministic and safe.

DATE_FORMATS = [
    "%d/%m/%Y",   # 21/03/2025
    "%Y-%m-%d",   # 2024-05-13  ← try ISO first since it's unambiguous
    "%d-%m-%Y",   # 10-08-2024
    "%m-%d-%Y",   # 02-26-2023
    "%d-%b-%Y",   # 20-Aug-2024
]

def parse_date(val):
    """
    Try each date format in DATE_FORMATS until one succeeds.

    Returns a date object on success, or pd.NaT (Not a Time) if every
    format fails or the value is missing. NaT is pandas' equivalent of
    NaN for datetime columns.
    """
    if pd.isna(val) or str(val).strip() == "":
        return pd.NaT
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(str(val).strip(), fmt).date()
        except ValueError:
            continue   # this format didn't match — try the next one
    return pd.NaT      # none of the formats matched

# Apply parse_date to each date column, then cast to pandas datetime type
for col in ["order_date", "ship_date"]:
    df[col] = df[col].apply(parse_date)
    df[col] = pd.to_datetime(df[col])
    bad = df[col].isna().sum()
    print(f"{col}: {bad} unparseable → NaT | range {df[col].min().date()} – {df[col].max().date()}")

# ── Catch impossible ship dates ───────────────────────────────────────────────
# A ship date before the order date is a data entry error.
# We nullify the ship_date (set to NaT) rather than dropping the row,
# because the rest of the order data is still valid.
mask_bad = (
    (df["ship_date"] < df["order_date"]) &
    df["ship_date"].notna() &
    df["order_date"].notna()
)
print(f"\nship_date < order_date: {mask_bad.sum()} rows → nullified")
df.loc[mask_bad, "ship_date"] = pd.NaT


# =============================================================================
# 6. HANDLE MISSING VALUES
# =============================================================================
section("6. HANDLE MISSING VALUES")

# Convert numeric-like columns from string to float/int before any imputation.
# errors='coerce' turns any value that can't be converted (e.g. "N/A", "")
# into NaN rather than raising an error.
for col in ["age", "unit_price", "total_amount", "qty", "discount_pct", "review_rating"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# ── Email ─────────────────────────────────────────────────────────────────────
# Strategy: sentinel fill
# We don't drop rows with missing emails — the order data is still useful.
# A sentinel value flags them for the CRM / marketing team to follow up.
n = df["email"].isna().sum()
df["email"] = df["email"].fillna("no_email@unknown.com")
print(f"  {'email':22s} FLAG     → {n} missing filled with sentinel")

# ── Phone ─────────────────────────────────────────────────────────────────────
# Strategy: sentinel fill (placeholder zeros)
# Same reasoning as email — keep the row, flag for follow-up.
n = df["phone"].isna().sum()
df["phone"] = df["phone"].fillna("000000000000")
print(f"  {'phone':22s} FLAG     → {n} missing filled with '000000000000'")

# ── Age ───────────────────────────────────────────────────────────────────────
# Strategy: median imputation
# Age is continuous. The median is more robust than the mean when there are
# outliers (which there are — we'll fix those in Step 8).
# We impute BEFORE fixing outliers so the outliers don't skew the median we use.
n = df["age"].isna().sum()
med_age = df["age"].median()
df["age"] = df["age"].fillna(med_age)
print(f"  {'age':22s} MEDIAN   → {n} missing filled with {med_age:.0f}")

# ── Order Date ────────────────────────────────────────────────────────────────
# Strategy: drop row
# An order without a date cannot be placed on any timeline.
# It's useless for trend analysis, cohort analysis, or fulfilment tracking.
n = df["order_date"].isna().sum()
df.dropna(subset=["order_date"], inplace=True)
df.reset_index(drop=True, inplace=True)
print(f"  {'order_date':22s} DROP     → {n} rows removed")

# ── Ship Date ─────────────────────────────────────────────────────────────────
# Strategy: keep NaT intentionally
# NaT here means "not yet shipped" — it carries real information.
# Filling it would be misleading.
n = df["ship_date"].isna().sum()
print(f"  {'ship_date':22s} KEEP NaT → {n} NaT retained (not yet shipped)")

# ── Review Rating ─────────────────────────────────────────────────────────────
# Strategy: keep NaN intentionally
# A missing rating means the customer chose not to review.
# This is different from a data entry error — it's a valid absence.
n = df["review_rating"].isna().sum()
print(f"  {'review_rating':22s} KEEP NaN → {n} NaN retained (no review given)")

# ── Marketing Source & Address ────────────────────────────────────────────────
# Strategy: fill with readable placeholder
# Keeps the row; signals clearly in the data that info was not captured.
for col, placeholder in [("marketing_source", "Unknown"),
                          ("address", "Address not provided")]:
    n = df[col].isna().sum()
    df[col] = df[col].fillna(placeholder)
    print(f"  {col:22s} FILL     → {n} filled with '{placeholder}'")


# =============================================================================
# 7. FIX DATA-TYPE ISSUES
# =============================================================================
section("7. FIX DATA-TYPE ISSUES")

# ── Phone ─────────────────────────────────────────────────────────────────────
# Because we loaded with dtype=str, phone numbers like 254797291993 are already
# strings. But some may have been stored as floats elsewhere and contain ".0".
# We strip that artefact, then zero-pad to 12 characters using zfill(12).
# zfill(12) adds leading zeros if the string is shorter than 12 chars:
#   e.g. "123" → "000000000123"
df["phone"] = (
    df["phone"]
      .str.replace(r"\.0$", "", regex=True)  # remove float artefact '254797.0' → '254797'
      .str.strip()
      .str.zfill(12)                          # pad to 12 digits with leading zeros
)
print(f"Phone sample : {df['phone'].head(3).tolist()}")

# ── Currency ──────────────────────────────────────────────────────────────────
# Strip any accidental whitespace and standardise to uppercase (KES / USD / EUR)
df["currency"] = df["currency"].str.strip().str.upper()
print(f"Currency vals: {df['currency'].unique()}")

# ── Numeric columns ───────────────────────────────────────────────────────────
# pd.to_numeric with errors='coerce' is safer than direct casting:
# if a cell contains "N/A" or "–", it becomes NaN instead of raising TypeError.
for col in ["unit_price", "total_amount", "discount_pct", "review_rating"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")
    print(f"  {col}: → {df[col].dtype}")

# Integer columns get fillna(0) before casting because int64 cannot hold NaN
# (unlike float64 which has a native NaN representation).
for col in ["qty", "age"]:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    print(f"  {col}: → {df[col].dtype}")


# =============================================================================
# 8. DETECT & CAP AGE OUTLIERS
# =============================================================================
section("8. DETECT & CAP AGE OUTLIERS")

# Ages of -4, 5, 12 and 130 were found in the raw data.
# We define a plausible customer age range of [16, 100].
# Anything outside this range is replaced with the median of VALID ages —
# not the overall median which would itself be skewed by the outliers.
AGE_MIN, AGE_MAX = 16, 100

# .between(a, b) returns True if AGE_MIN <= value <= AGE_MAX (inclusive)
valid_mask   = df["age"].between(AGE_MIN, AGE_MAX)
median_age   = int(df.loc[valid_mask, "age"].median())  # median of valid ages only
outlier_mask = ~valid_mask                               # ~ is the boolean NOT operator

print(f"Age outliers (< {AGE_MIN} or > {AGE_MAX}): {outlier_mask.sum()} rows")
print(f"  Outlier values: {sorted(df.loc[outlier_mask, 'age'].tolist())}")

# df.loc[mask, col] = value  sets column values only where mask is True
df.loc[outlier_mask, "age"] = median_age
print(f"  Replaced with median age: {median_age}")


# =============================================================================
# 9. VALIDATE EMAIL ADDRESSES
# =============================================================================
section("9. VALIDATE EMAIL ADDRESSES")

# A regex (regular expression) is a pattern that describes what a string
# should look like. We use it to check whether each email is well-formed.
#
# Pattern breakdown:
#   ^               → start of string
#   [\w.%+\-]+      → one or more of: word chars, dot, %, +, hyphen
#                     (this is the local part before the @)
#   @               → literal @ symbol
#   [\w.\-]+        → one or more of: word chars, dot, hyphen
#                     (this is the domain name, e.g. "gmail")
#   \.              → literal dot
#   [a-zA-Z]{2,}   → two or more letters (the TLD, e.g. "com", "co.ke")
#   $               → end of string
#
# re.compile() pre-compiles the pattern for efficiency — faster than
# recompiling on every row when calling .apply() over thousands of rows.

EMAIL_RE = re.compile(r"^[\w.%+\-]+@[\w.\-]+\.[a-zA-Z]{2,}$")

# Emails we filled in as sentinels earlier — we know these are not real
SENTINEL_EMAILS = {"no_email@unknown.com", "nan", ""}

def is_valid_email(val):
    """
    Return True if val is a syntactically valid email address.
    Sentinel / missing values always return False.
    Uses a compiled regex for efficiency.
    """
    s = str(val).strip()
    if s in SENTINEL_EMAILS:
        return False
    return bool(EMAIL_RE.match(s))   # .match() returns a Match object or None

# We add a NEW column instead of modifying or dropping rows.
# This is non-destructive: the analyst can decide what to do with invalid emails.
df["email_valid"] = df["email"].apply(is_valid_email)
invalid = (~df["email_valid"]).sum()
print(f"Invalid / missing emails flagged: {invalid} ({invalid/len(df)*100:.1f}%)")
print(f"Valid emails: {df['email_valid'].sum()}")


# =============================================================================
# 10. NORMALISE TOTAL AMOUNT → KES
# =============================================================================
section("10. NORMALISE TOTAL AMOUNT → KES")

# The total_amount column contains values in three different currencies.
# Comparing or summing them directly is meaningless — like adding apples and oranges.
# We create a NEW column (total_kes) with everything in one currency (KES).
# The original total_amount and currency columns are PRESERVED so no data is lost.
#
# FX_TO_KES maps each currency code to its conversion rate INTO KES.
# In production you would pull live rates from an API (e.g. exchangeratesapi.io)
# and log the retrieval date so results are reproducible.

FX_TO_KES = {
    "KES": 1.0,    # already in KES — multiply by 1 (no change)
    "USD": 129.5,  # 1 USD ≈ 129.5 KES
    "EUR": 140.2,  # 1 EUR ≈ 140.2 KES
}

# .apply(func, axis=1) passes each ROW (as a Series) to the function.
# axis=1 means "apply across columns" (i.e. row by row).
# We access row["total_amount"] and row["currency"] to compute the KES equivalent.
# .get(key, default) returns np.nan for any currency code not in our map.
df["total_kes"] = df.apply(
    lambda row: row["total_amount"] * FX_TO_KES.get(row["currency"], np.nan),
    axis=1
)

print(f"FX rates used: {FX_TO_KES}")
print(f"\ntotal_kes summary:\n{df['total_kes'].describe().round(2)}")


# =============================================================================
# 11. EXPORT + CLEANING REPORT
# =============================================================================
section("11. EXPORT CLEAN DATASET + SUMMARY REPORT")

df.to_csv(CLEAN_PATH, index=False)   # index=False prevents pandas writing the row number as a column
print(f"✓ Clean CSV saved → {CLEAN_PATH}")
print(f"  Final shape: {df.shape}")

print("\n── Remaining nulls ──")
nulls = df.isnull().sum()
remaining = nulls[nulls > 0]
print(remaining if not remaining.empty else "None!")

print("\n── Final dtypes ──")
print(df.dtypes)

print("\n── Sample of clean data (3 rows) ──")
preview_cols = ["order_id", "customer_name", "city", "category", "order_status", "total_kes"]
print(df[preview_cols].head(3).to_string())

print(f"\n{'='*65}")
print("  CLEANING COMPLETE")
print(f"{'='*65}\n")
