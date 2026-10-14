# importing duckdb library
import duckdb

# analysis window: 2026 is still in progress, so it is left out of trend comparisons
START_YEAR = 2020
END_YEAR = 2025

# creating a connection to a db using duckdb
conn = duckdb.connect('funding.duckdb')

#  loading the country csv files into a table called plans
conn.sql(
    """
    CREATE OR REPLACE TABLE Plans AS
    SELECT *
    FROM read_csv('data/fts_requirements_funding_???.csv',
    nullstr='None',
    union_by_name=true)
    """
)

#  loading the sector csv files into a table called clusters
conn.sql(
    """
    CREATE OR REPLACE TABLE Clusters AS
    SELECT *
    FROM read_csv('data/fts_requirements_funding_cluster_*.csv',
    nullstr='None',
    union_by_name=true)
    """
)

# checking for row count in each table
print("Row Count:")
print(
    conn.sql(
        "SELECT 'Plans' AS X, COUNT(*) Y FROM Plans UNION ALL SELECT 'Clusters' AS X, COUNT(*) Y FROM Clusters  "
    ).df()
)

#  checking the  columns in the plans table
print(conn.sql("DESCRIBE Plans").df().to_string())

# FIX 1: funding gap by country and year, using ONLY rows that have requirements.
# Rows with funding but no requirements (money not linked to a plan, and future-year
# pledges) used to be added to the funded total but not the needed total, which
# pushed the % funded up. They are analysed separately further down.

# funding gap by country and year
print('Funding Vs Needed By Country and Year (plan rows only)')
gap = conn.sql(f"""
    SELECT countryCode,
    Year,
    SUM(TRY_CAST(requirements AS DOUBLE)) AS Needed,
    SUM(TRY_CAST(funding AS DOUBLE)) AS Funded,
    ROUND(100.0 * SUM(TRY_CAST(funding AS DOUBLE)) / SUM(TRY_CAST(requirements AS DOUBLE)), 1) AS pct_funded
    FROM Plans
    WHERE TRY_CAST(requirements AS DOUBLE) > 0
      AND Year BETWEEN {START_YEAR} AND {END_YEAR}
    GROUP BY countryCode, Year
    ORDER BY countryCode, Year
    """
).df()

print(gap.to_string())
gap.to_csv("funding_gap_by_country_year.csv", index=False)

# ---------------------------------------------------------------------------
# FIX 2: one row per plan (HRP, flash appeal, etc.) so each row can be checked
# against the original CSV. pct_funded_csv is the value FTS reports (whole numbers),
# so expect pct_funded to differ from it by up to about 1 point because of rounding.
# ---------------------------------------------------------------------------

# funding gap by plan
print('Funding Vs Needed By Plan')
gap_by_plan = conn.sql(f"""
    SELECT countryCode,
    Year,
    typeName,
    name AS plan_name,
    TRY_CAST(requirements AS DOUBLE) AS Needed,
    TRY_CAST(funding AS DOUBLE) AS Funded,
    ROUND(100.0 * TRY_CAST(funding AS DOUBLE) / TRY_CAST(requirements AS DOUBLE), 1) AS pct_funded,
    TRY_CAST(percentFunded AS DOUBLE) AS pct_funded_csv
    FROM Plans
    WHERE TRY_CAST(requirements AS DOUBLE) > 0
      AND Year BETWEEN {START_YEAR} AND {END_YEAR}
    ORDER BY countryCode, Year, typeName
    """
).df()

print(gap_by_plan.to_string())
gap_by_plan.to_csv("funding_gap_by_plan.csv", index=False)

# Funding that is NOT linked to any plan (blank requirements).

print('Funding Outside Plans')
outside = conn.sql(f"""
    SELECT countryCode,
    Year,
    ROUND(SUM(TRY_CAST(funding AS DOUBLE)) FILTER (WHERE TRY_CAST(requirements AS DOUBLE) IS NULL) / 1e6, 1) AS outside_plan_musd,
    ROUND(SUM(TRY_CAST(funding AS DOUBLE)) / 1e6, 1) AS all_funding_musd,
    ROUND(100.0 * SUM(TRY_CAST(funding AS DOUBLE)) FILTER (WHERE TRY_CAST(requirements AS DOUBLE) IS NULL)
          / SUM(TRY_CAST(funding AS DOUBLE)), 1) AS pct_of_funding_outside_plans
    FROM Plans
    WHERE Year BETWEEN {START_YEAR} AND {END_YEAR}
    GROUP BY countryCode, Year
    ORDER BY countryCode, Year
    """
).df()

print(outside.to_string())
outside.to_csv("funding_outside_plans.csv", index=False)

#  checking the  columns in the clusters table
print(conn.sql("DESCRIBE Clusters").df().to_string())

# checking for  distinct clusters in the clusters  table (Gives a list containing each cluster)
print(conn.sql("SELECT DISTINCT cluster FROM clusters ORDER BY cluster").df().to_string())

# checking the number of distinct clusters (Gives a number)
print(conn.sql("SELECT COUNT(DISTINCT clusterCode) FROM clusters ").df().to_string())

sectors = conn.sql(f"""
    SELECT countryCode,
           sector,
           ROUND(SUM(TRY_CAST(requirements AS DOUBLE)) / 1e6, 1) AS needed_musd,
           ROUND(SUM(TRY_CAST(funding AS DOUBLE)) / 1e6, 1) AS funded_musd,
           ROUND(100.0 * SUM(TRY_CAST(funding AS DOUBLE))
                 / SUM(TRY_CAST(requirements AS DOUBLE)), 1) AS pct_funded
    FROM (
        SELECT *,
               CASE
                   -- Others (groups under 14 variants), checked first so
                   -- "Early Recovery and Livelihoods" doesn't fall into Food
                   WHEN c LIKE '%recovery%' OR c LIKE 'releve%' OR c LIKE 'retour%'
                     OR c LIKE '%return%' OR c LIKE '%reintegration%'
                     OR c LIKE '%not specified%' OR c LIKE '%not yet specified%'
                     OR c LIKE '%non specifi%' OR c = 'other' OR c = 'transversales'
                     OR c LIKE '%ukraine humanitarian%'
                     OR c LIKE '%infrastructure%' OR c LIKE '%governance%'
                     OR c LIKE '%development%' OR c = 'ddr'
                     OR c LIKE '%cholera%' OR c LIKE '%preparedness%'
                     OR c = 'all covid-19' OR c LIKE '%acces%reduite%'
                   THEN 'Others'

                   -- CCCM and site management (14 variants)
                   WHEN c LIKE '%cccm%' OR c LIKE '%camp%' OR c LIKE '%site management%'
                     OR c LIKE '%dtm%' OR c LIKE '%displacement tracking%'
                   THEN 'CCCM'

                   -- Shelter and NFI (46)
                   WHEN c LIKE '%shelter%' OR c LIKE '%nfi%' OR c LIKE '%abris%'
                     OR c LIKE '%non-food%' OR c LIKE '%non food%'
                     OR c LIKE '%non alimentaire%' OR c LIKE '%non-alimentaire%'
                     OR c LIKE '%articles menagers%'
                   THEN 'Shelter and NFI'

                   -- Multi-purpose cash (18)
                   WHEN c LIKE '%cash%' OR c LIKE '%multi-purpose%' OR c LIKE '%multipurpose%'
                     OR c LIKE '%usage%multiple%' OR c LIKE '%usages multiples%'
                     OR c LIKE '%especes%' OR c LIKE '%monetaires%' OR c LIKE 'job creation%'
                   THEN 'Multi-purpose Cash'

                   -- Protection and Mine Action (23)
                   WHEN c LIKE '%protection%' OR c LIKE '%mine action%'
                     OR c LIKE '%human rights%' OR c LIKE '%gender%' OR c LIKE '%violence%'
                   THEN 'Protection'

                   -- Logistics and telecoms (17)
                   WHEN c LIKE '%logisti%' OR c LIKE '%telecom%'
                   THEN 'Logistics and Telecoms'

                   -- Coordination, common services and support (28)
                   WHEN c LIKE '%coordination%' OR c LIKE '%common services%'
                     OR c LIKE '%common humanitarian fund%' OR c LIKE '%enabling services%'
                     OR c LIKE '%support services%' OR c LIKE '%soutien%'
                   THEN 'Coordination and Support'

                   -- Multi-sector and refugee response (21)
                   WHEN c LIKE '%multi%' OR c LIKE '%refugee%' OR c LIKE '%refugie%'
                     OR c LIKE '%sectorielle%' OR c LIKE '%cross-sector%'
                   THEN 'Multi-sector and Refugee'

                   -- The four main sectors
                   WHEN c LIKE '%health%' OR c LIKE '%sante%' THEN 'Health'

                   WHEN c LIKE '%wash%' OR c LIKE '%water%' OR c LIKE '%sanitation%'
                     OR c LIKE '%hygiene%' OR c LIKE '%assainissement%'
                     OR c LIKE 'eau %' OR c LIKE 'eau,%'
                   THEN 'WASH'

                   WHEN c LIKE '%education%' THEN 'Education'

                   WHEN c LIKE '%food%' OR c LIKE '%agricultur%' OR c LIKE '%livelihood%'
                     OR c LIKE '%alimentaire%'
                   THEN 'Food'

                   -- Nutrition checked after Food, so "Food Security and Nutrition"
                   -- stays in Food, then folded into Health
                   WHEN c LIKE '%nutrition%' THEN 'Health'

                   ELSE 'Others'
               END AS sector
        FROM (
            SELECT *, lower(strip_accents(trim(cluster))) AS c
            FROM clusters
        )
    )
    WHERE Year BETWEEN {START_YEAR} AND {END_YEAR}
        AND TRY_CAST(requirements AS DOUBLE) > 0
    GROUP BY countryCode, sector
    ORDER BY countryCode, pct_funded
""").df()

print(sectors.to_string())
sectors.to_csv("sector_funding_gap.csv", index=False)