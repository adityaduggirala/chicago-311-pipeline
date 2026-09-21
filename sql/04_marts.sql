-- Mart 1: daily request volume by type
CREATE OR REPLACE TABLE mart_daily_volume AS
SELECT f.created_date, d.sr_type, count(*) AS requests
FROM fct_requests f JOIN dim_request_type d USING (request_type_key)
GROUP BY 1, 2;

-- Mart 2: resolution-time SLA stats by request type (closed tickets only)
CREATE OR REPLACE TABLE mart_resolution_by_type AS
SELECT d.sr_type,
       d.owner_department,
       count(*)                                        AS closed_requests,
       round(median(f.resolution_hours), 1)            AS median_hours,
       round(quantile_cont(f.resolution_hours, 0.9), 1) AS p90_hours
FROM fct_requests f JOIN dim_request_type d USING (request_type_key)
WHERE f.closed_at IS NOT NULL AND f.resolution_hours >= 0
GROUP BY 1, 2;

-- Mart 3: open backlog by ward, with rank
CREATE OR REPLACE TABLE mart_ward_backlog AS
SELECT ward,
       count(*) FILTER (WHERE is_open)                   AS open_requests,
       count(*)                                          AS total_requests,
       round(100.0 * count(*) FILTER (WHERE is_open) / count(*), 2) AS pct_open,
       rank() OVER (ORDER BY count(*) FILTER (WHERE is_open) DESC) AS backlog_rank
FROM fct_requests
WHERE ward IS NOT NULL
GROUP BY ward;

-- Mart 4: 7-day rolling average of daily volume (window function)
CREATE OR REPLACE TABLE mart_volume_trend AS
WITH daily AS (
    SELECT created_date, count(*) AS requests FROM fct_requests GROUP BY 1
)
SELECT created_date, requests,
       round(avg(requests) OVER (ORDER BY created_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 1) AS rolling_7d_avg
FROM daily
ORDER BY created_date;
