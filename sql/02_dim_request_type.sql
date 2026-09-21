CREATE OR REPLACE TABLE dim_request_type AS
SELECT
    row_number() OVER (ORDER BY sr_type) AS request_type_key,
    sr_type,
    any_value(sr_short_code)             AS sr_short_code,
    any_value(owner_department)          AS owner_department
FROM stg_requests
WHERE sr_type IS NOT NULL
GROUP BY sr_type;
