# Replicating OCHA FTS Funding Coverage with SQL in Python

If I worked with the raw humanitarian funding data myself, would I get the same "% funded" figures that OCHA publishes?
This project tests that using SQL (DuckDB) run from Python, on funding data for DRC, Haiti, Palestine, Sudan and Ukraine, 2020-2025.

I built it to practise running SQL from Python for the first time, and to check my own analysis against a published source.

## Result

**My figures match the published FTS figures.** Across all 34 plan-level rows, the largest difference from FTS's `percentFunded` was 0.5 percentage points and the average was 0.3. FTS reports whole numbers, so the remaining differences are rounding.

A sample of the comparison:

| Country | Year | Plan type | My % funded | FTS % funded | Difference |
|---|---|---|---|---|---|
| DRC | 2020 | Humanitarian response plan | 41.9 | 42 | 0.1 |
| Haiti | 2022 | Flash appeal | 9.9 | 10 | 0.1 |
| Palestine | 2021 | Flash appeal | 49.5 | 49 | 0.5 |
| Palestine | 2023 | Flash appeal | 103.6 | 104 | 0.4 |
| Sudan | 2024 | Humanitarian needs and response plan | 70.0 | 70 | 0.0 |
| Ukraine | 2022 | Flash appeal | 87.7 | 88 | 0.3 |

The full comparison is in `funding_gap_by_plan.csv` (columns `pct_funded` and `pct_funded_csv`).

## Where my numbers first did not match

My first version of the query summed funding and requirements across every row for a country and year, then divided. That gave results far from FTS. For Palestine in 2023 it produced about 186%, against 99% and 104% for the two plans in FTS.

The cause: the FTS files include rows that have funding but no requirements. These are funds not linked to any response plan, and pledges for future years. My first query added that funding to the numerator but had nothing to add to the denominator.

The fix was to use only rows that have requirements, which removed the mismatch. I kept the excluded funding in its own table (`funding_outside_plans.csv`) so it isn't lost.

## Approach

1. Load the per-country FTS CSV files into DuckDB tables using a file pattern (`read_csv` with `union_by_name`)
2. Calculate % funded as total funding / total requirements, summed across plans, not as an average of plan percentages
3. Compare my percentage with FTS's reported percentage for every plan
4. Investigate and fix any mismatch (see above)

## SQL techniques used

Running SQL from Python (DuckDB) and exporting results with pandas, `TRY_CAST` for messy columns, aggregation with `GROUP BY`, `FILTER` clauses, subqueries, `CASE` with `LIKE` pattern matching, text cleaning (`lower`, `trim`, `strip_accents`), and `ROUND`.

## Combined totals by country and year

FTS publishes percentages per plan. Where a country has two plans in a year (for example a response plan and a flash appeal), I also calculated the combined figure from the same rows. These combined values are my own calculation, not FTS figures.

| | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| DRC | 41.9 | 43.8 | 53.4 | 42.5 | 51.4 | 26.9 |
| Haiti | 32.5 | 33.9 | 40.0 | 34.4 | 44.5 | 26.7 |
| Palestine | 77.9 | 82.6 | 91.4 | 101.8 | 84.8 | 67.3 |
| Sudan | 53.4 | 37.9 | 57.5 | 51.4 | 70.0 | 40.0 |
| Ukraine | 60.5 | 63.4 | 87.7 | 73.8 | 75.7 | 63.2 |

## Extra: observations from the results

- Coverage fell in all five countries in 2025. Combined, requirements rose 15% to $14.3B and funding fell 20% to $7.0B (70.3% to 48.9%)
- About 22% of funding recorded for these countries was not linked to a plan (37.8% in Palestine), which is why plan-only and all-funding figures differ
- `sector_funding_gap.csv` groups FTS's many sector names into about 12 standard sectors. The grouping is my own, so it is not part of the validation

## Files

- `analyze.py`: loads the CSVs into DuckDB and runs all queries
- `funding_gap_by_plan.csv`: one row per plan, my % funded vs FTS-reported %
- `funding_gap_by_country_year.csv`: combined coverage by country and year
- `funding_outside_plans.csv`: funding not linked to a plan
- `sector_funding_gap.csv`: coverage by country and sector

## How to run

```
pip install duckdb
python analyze.py
```

## Limitations

- Only five countries and plans with requirements are included
- 2026 is excluded because the year is still in progress
- Differences of up to 0.5 points come from FTS rounding to whole numbers
- Aggregated organisational data only; no personal data is used

## Attribution

Data: OCHA Financial Tracking Service (https://fts.unocha.org), via the Humanitarian Data Exchange.
