# Campaign Ledger

An independent marketing analytics prototype by Marina Avetisian, built through AI-assisted development. It imports fictional campaign exports into SQLite, calculates campaign metrics with SQL, and produces an interactive report that opens without a server.

## Run

Python 3 with its standard library is sufficient. From this folder:

```sh
python3 generate_sample.py
python3 build_report.py
python3 -m unittest -v test_report.py
```

Open `output/index.html`. Filter by channel and reporting window, inspect campaign metrics and rule-based alerts, change the lifetime-value assumptions, or export the displayed campaign table as CSV.

## Implemented

- Four fictional campaigns across Meta and Google labels. These labels identify sample channels; no accounts are connected.
- CSV schema and date validation, nonnegative amounts, foreign keys, unique keys, and order attribution consistency checks.
- A transactional import: failed replacements preserve the earlier database snapshot. Repeated valid imports do not duplicate records.
- SQL calculations for advertising spend, gross attributed revenue, new customers, CAC, ROAS, and average order value. Each source is aggregated before joining to avoid multiplying amounts.
- Interactive channel and reporting-window filters; CSV export; deterministic week-over-week change alerts.
- An editable revenue LTV calculator, clearly labeled as an assumption-based estimate.

## Metric definitions

- CAC = (ad spend + the other acquisition costs represented in the fixture) / unique new customers acquired during the reporting window. The demo's other costs are sample allocations, not a claim about any company's accounting.
- ROAS = gross order revenue attributed to campaigns during the window / ad spend during the window. Repeat purchases count as revenue but do not become additional new customers.
- Estimated revenue LTV = average order value × orders per year × customer lifespan in years. This is not a prediction trained on the 14-day dataset and does not include profit margin or refunds.

All amounts use USD; money is stored as integer cents. Zero denominators are unavailable, not zero. Attribution is simplified and mutually exclusive: each customer and order has one assigned campaign. Dates are fictional reporting dates, not a live feed.

## Tables

`campaigns` defines the channel and campaign name. `daily_spend` has one row per campaign and day. `customers` records one acquisition campaign and date per customer. `orders` stores individual attributed purchases. SQL source files are in `sql/`.

## Workflow extension

The HTTP-to-SQL workflow, refund-aware calculations, import history, corrected-record handling, and optional Claude adapter are described in [Workflow operations](integrations/README.md). The public Site replays verified sample outcomes; it does not run the backend on visitor requests.

## Deliberately unfinished

No live Meta/Google API connectors, webhook ingestion, scheduling, or autonomous advertising actions are implemented. An optional local Claude adapter is implemented and tested with simulated responses; no live model call is verified or deployed. Alerts and summaries in this version are deterministic. A future agent could use the SQL report as its input and draft an explanation for human review; it should cite the metrics rather than invent causes.

A live integration would need authorized advertising and store data, attribution reconciliation, currency/time-zone handling, and operational monitoring. The workflow extension demonstrates retries, refund validation, and completeness checks against fictional full snapshots; it is not a live integration.

## Sources

- [Shopify CAC definition](https://www.shopify.com/blog/ecommerce-customer-acquisition)
- [Shopify ROAS definition](https://www.shopify.com/blog/roas)
- [Shopify LTV model](https://www.shopify.com/blog/customer-lifetime-value-analysis)

## Suggested project description after reviewing the implementation

Built a Python/SQLite marketing analytics prototype that validates campaign exports, calculates CAC and ROAS with SQL, flags sample week-over-week changes, and generates an interactive dashboard with an assumption-based LTV calculator. Developed through AI-assisted iteration using fictional data.
