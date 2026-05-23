# 🧹 E-Commerce Data Cleaning — Portfolio Project

A end-to-end data cleaning project on a real-world-style East Africa e-commerce orders dataset. The project identifies, documents, and resolves 10 categories of data quality problems using Python and pandas, transforming 5,115 messy rows into a reliable, analysis-ready dataset.

---

## 📁 Project Structure

```
├── messy_data__1_.csv          # Raw input dataset (5,115 rows × 21 columns)
├── data_cleaning_portfolio.py  # Main cleaning script
├── orders_clean.csv            # Output: cleaned dataset (4,831 rows × 23 columns)
└── README.md                   # This file
```

---

## 📦 Dataset Description

| Property | Detail |
|---|---|
| Domain | E-commerce orders — East Africa |
| Raw size | 5,115 rows × 21 columns |
| Clean size | 4,831 rows × 23 columns |
| Coverage | Orders from Kenya, Uganda, Tanzania (2023–2025) |

### Columns

| Column | Description |
|---|---|
| `order_id` | Unique order identifier (e.g. ORD-103321) |
| `customer_id` | Customer identifier |
| `customer_name` | Full name of the customer |
| `email` | Customer email address |
| `phone` | Customer phone number (East Africa format) |
| `city` | Delivery city / town |
| `age` | Customer age in years |
| `order_date` | Date the order was placed |
| `ship_date` | Date the order was shipped |
| `category` | Product category (e.g. electronics, clothing) |
| `product_name` | Name of the product ordered |
| `qty` | Quantity ordered |
| `unit_price` | Price per unit |
| `discount_pct` | Discount percentage applied |
| `currency` | Transaction currency (KES / USD / EUR) |
| `total_amount` | Total order value in original currency |
| `payment_method` | How the customer paid |
| `order_status` | Current status of the order |
| `review_rating` | Customer review score (1–5), if provided |
| `marketing_source` | How the customer found the store |
| `address` | Full delivery address |
| `email_valid` | *(Added)* Boolean — whether the email passed regex validation |
| `total_kes` | *(Added)* Total amount converted to KES |

---

## 🔍 Data Quality Issues Found

Before any cleaning, the raw dataset had the following problems:

| Issue | Count / Detail |
|---|---|
| Duplicate order IDs | 115 duplicate rows |
| Inconsistent column names | Whitespace, mixed casing, special chars (`/`, `-`, `()`, `%`) |
| Mixed Order Status variants | 17 variants for 6 logical statuses (e.g. `"Pending"`, `"PENDING"`, `"pending"`) |
| Mixed Payment Method variants | 17 variants for 4 methods (e.g. `"M-PESA"`, `"Mpesa"`, `"mobile money"`) |
| Mixed Product Category variants | 24 variants for 7 categories (e.g. `"Electrnics"`, `"ELEC"`, `"Beauti"`) |
| Mixed City variants | Leading/trailing spaces, abbreviations (`"NBO"`, `"KSM"`, `"KLA"`, `"Nairobii"`) |
| Mixed date formats | 5 formats in one column (`21/03/2025`, `2024-05-13`, `10-08-2024`, `02-26-2023`, `20-Aug-2024`) |
| Impossible ship dates | 418 rows where `ship_date < order_date` |
| Missing values | Across 7 columns (email: 218, phone: 176, age: 110, order_date: 95, ship_date: 96, review_rating: 1,403, marketing_source: 623) |
| Phone stored as float | Scientific notation (e.g. `2.547973e+11`) instead of string |
| Age outliers | 39 rows with impossible ages (negative values, age 5, age 130) |
| Mixed currencies | Amounts in KES, USD, and EUR in the same column with no unified base |

---

## 🛠️ Cleaning Steps & Methodology

Each decision is documented below — including *why* a particular strategy was chosen.

### 1. Fix Column Names
**Problem:** 21 columns had inconsistent naming — whitespace padding, `UPPER_CASE`, `camelCase`, special characters like `(`, `)`, `/`, `%`, `-`, and `?`.

**Solution:** Applied a regex pipeline to strip, lowercase, and replace all symbols with underscores, then renamed to short, readable snake_case names.

**Why:** Inconsistent names cause `KeyError` bugs and make code harder to read. Standardising upfront prevents every downstream operation from needing workarounds.

---

### 2. Remove Duplicate Orders
**Problem:** 115 rows shared an `order_id` with another row.

**Solution:** Kept the first occurrence per `order_id` using `drop_duplicates(keep='first')`.

**Why:** Duplicate orders inflate revenue figures, distort customer counts, and corrupt any aggregation. The "keep first" strategy preserves the earliest recorded version, which is most likely the authoritative record.

---

### 3. Standardise Categorical Columns
**Problem:** Free-text entry created dozens of variants for fields that should have a small fixed set of values.

| Column | Raw variants | After cleaning |
|---|---|---|
| Order Status | 17 | 6 |
| Payment Method | 17 | 4 |
| Product Category | 24 | 7 |
| City | Many (spaces, abbreviations, typos) | 9 normalised |

**Solution:** Built a `{canonical: [variants]}` lookup dictionary for each column and applied it via `.apply()`. Unknown values fall through to `"other"` rather than being silently dropped.

**Why:** Inconsistent categories make groupby analysis useless — `df.groupby('category')` on the raw data would return 24 groups instead of 7. The variant-mapping approach is transparent, auditable, and easy to extend.

---

### 4. Parse & Validate Dates
**Problem:** The `order_date` column contained at least 5 different date formats. Additionally, 418 rows had a `ship_date` that was *earlier* than the `order_date` — physically impossible.

**Solution:** Tried each format in sequence using `datetime.strptime`; any value that failed all formats became `NaT`. Rows where `ship_date < order_date` had the ship date nullified.

**Why:** Pandas' `pd.to_datetime(infer=True)` can silently mis-parse ambiguous formats like `10-08-2024` (Aug 10 vs Oct 8). Explicit format-by-format parsing is slower but deterministic. Nullifying impossible ship dates rather than dropping the rows preserves the order data — the ship date just needs re-entry.

---

### 5. Handle Missing Values
Different columns got different strategies because the *reason* for missingness differs:

| Column | Strategy | Rationale |
|---|---|---|
| `email` | Sentinel string `no_email@unknown.com` | Row is still useful; flag for follow-up |
| `phone` | Sentinel string `000000000000` | Same — don't lose the order record |
| `age` | Median imputation | Continuous variable; median is robust to skew |
| `order_date` | Drop row | A date-less order cannot be placed in any timeline |
| `ship_date` | Keep `NaT` | `NaT` legitimately means "not yet shipped" |
| `review_rating` | Keep `NaN` | Customer chose not to review — not the same as a missing error |
| `marketing_source` | Fill with `"Unknown"` | Keeps the row; signals data was not captured |
| `address` | Fill with `"Address not provided"` | Keeps the row; flags for logistics follow-up |

---

### 6. Fix Data-Type Issues
**Problem:** Phone numbers were loaded as a float column in scientific notation (`2.547973e+11`) because pandas inferred numeric type. Currency amounts spanned three different denominations with no normalisation.

**Solution:** Converted phone to a zero-padded 12-character string. Cast all numeric columns explicitly. Loaded the full file as `dtype=str` initially to avoid losing leading characters before any cleaning.

**Why:** A phone number is an identifier, not a number — arithmetic on it is meaningless. Loading as `str` first is the correct defensive pattern when any column might be misidentified.

---

### 7. Detect & Cap Age Outliers
**Problem:** 39 rows had ages outside a plausible customer range — values of -4, 5, 12, and 130.

**Solution:** Defined the valid range as `[16, 100]`. Outliers were replaced with the median of valid ages (47).

**Why:** Dropping outlier rows would discard valid order data — the age field is wrong but the rest of the row is fine. Capping to the median is a conservative imputation that doesn't introduce extreme values. A flag column could also be added if the analyst wants to track which ages were imputed.

---

### 8. Validate Email Addresses
**Problem:** 218 emails were missing, and additional emails may be malformed.

**Solution:** Applied a standard regex pattern and added a boolean `email_valid` column rather than dropping or modifying any rows.

**Why:** Adding a validation flag is non-destructive — it surfaces the problem without making data decisions on behalf of the analyst. The marketing team can then filter for `email_valid == False` and run a re-engagement campaign.

---

### 9. Normalise Currency → KES
**Problem:** `total_amount` contained values in KES, USD, and EUR in the same column. Direct comparison or summation across currencies would produce meaningless results.

**Solution:** Added a `total_kes` column by multiplying each row's amount by a fixed exchange rate. The original `total_amount` and `currency` columns are preserved.

**Why:** Preserving the original currency data is important — converting in-place destroys information. The new column makes cross-currency analysis possible while keeping the raw figures intact. In production, rates would be pulled from a live FX API and the conversion date logged.

---

## ▶️ How to Run

### Prerequisites

- Python 3.8+
- pandas
- numpy

### Installation

```bash
pip install pandas numpy
```

### Run the script

```bash
# Place messy_data__1_.csv in the same folder, then:
python data_cleaning_portfolio.py
```

### Output

The script produces `orders_clean.csv` in the same directory and prints a full cleaning log to the terminal.

---

## 📊 Before vs After

| Metric | Raw | Clean |
|---|---|---|
| Rows | 5,115 | 4,831 |
| Columns | 21 | 23 |
| Duplicate orders | 115 | 0 |
| Order Status variants | 17 | 6 |
| Payment Method variants | 17 | 4 |
| Product Category variants | 24 | 7 |
| Date formats | 5+ | 1 (ISO 8601) |
| Impossible ship dates | 418 | 0 |
| Phone dtype | float (scientific notation) | str (zero-padded) |
| Age outliers | 39 | 0 |
| Currencies in total_amount | 3 (mixed) | 3 preserved + 1 unified KES column |

---

## 💡 What I Learned

**1. Data problems are rarely random — they have a story.**
Most issues traced back to a specific cause: free-text dropdowns (category variants), copy-paste from different systems (date formats), and form fields with no validation (negative ages, impossible ship dates). Understanding *why* data is dirty helps you write more targeted fixes and anticipate the same problems in future datasets.

**2. Every null is not the same null.**
The biggest mindset shift was treating missing values as carrying information. A missing `ship_date` means the order hasn't shipped yet. A missing `review_rating` means the customer didn't review. A missing `order_date` means the row is unusable. Applying a blanket `.fillna(0)` or `.dropna()` would have destroyed that signal.

**3. The reason behind a cleaning decision matters as much as the decision itself.**
Dropping vs imputing vs flagging all produce valid-looking data. What separates a good data analyst from a careless one is the ability to articulate *why* a particular strategy was appropriate for that specific column — and document it so the next person doesn't have to guess.

**4. Load data defensively.**
Reading everything as `dtype=str` first, then casting explicitly column by column, prevents pandas from making type assumptions that silently corrupt data (like turning phone numbers into floats).

**5. Cleaning is iterative, not linear.**
Several issues only became visible after fixing earlier ones — the age outliers, for example, were masked until the column was properly cast to numeric. Real cleaning requires going back and forth, not just running through a checklist once.

**6. Non-destructive changes preserve optionality.**
Adding a `total_kes` column instead of overwriting `total_amount`, and adding `email_valid` instead of dropping invalid emails, keeps the original data intact. Downstream analysts can make their own decisions about what to do with flagged rows.

**7. Standardisation before analysis is non-negotiable.**
Running `groupby('order_status')` on the raw data would return 17 groups. After standardisation, it returns 6. Every analysis and visualisation built on uncleaned categoricals would have been wrong — and the errors would have been hard to spot.

---

## 🛠️ Tech Stack

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.8+ | Core language |
| pandas | 2.x | Data manipulation |
| numpy | 1.x | Numerical operations, NaN handling |
| re (stdlib) | — | Email regex validation |
| datetime (stdlib) | — | Multi-format date parsing |

---

## 👤 Author

**Your Name**
[GitHub](https://github.com/yourusername) · [LinkedIn](https://linkedin.com/in/yourprofile)

---

## 📄 License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).
