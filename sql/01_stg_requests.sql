-- Staging: latest version of each ticket, typed and cleaned.
CREATE OR REPLACE TABLE stg_requests AS
WITH ranked AS (
    SELECT *,
           row_number() OVER (
               PARTITION BY sr_number
               ORDER BY last_modified_date DESC, _loaded_at DESC
           ) AS rn
    FROM raw_requests
    WHERE sr_number IS NOT NULL
)
SELECT
    sr_number,
    trim(sr_type)                                   AS sr_type,
    sr_short_code,
    owner_department,
    CASE WHEN status IN ('Open','Completed','Canceled') THEN status
         WHEN status ILIKE 'open%' THEN 'Open'
         WHEN status ILIKE 'complet%' THEN 'Completed'
         WHEN status ILIKE 'cancel%' THEN 'Canceled'
         ELSE coalesce(status, 'Unknown') END       AS status,
    origin,
    TRY_CAST(created_date AS TIMESTAMP)             AS created_at,
    TRY_CAST(last_modified_date AS TIMESTAMP)       AS modified_at,
    TRY_CAST(closed_date AS TIMESTAMP)              AS closed_at,
    zip_code,
    TRY_CAST(community_area AS INTEGER)             AS community_area,
    TRY_CAST(ward AS INTEGER)                       AS ward,
    TRY_CAST(latitude AS DOUBLE)                    AS latitude,
    TRY_CAST(longitude AS DOUBLE)                   AS longitude,
    date_diff('minute', TRY_CAST(created_date AS TIMESTAMP), TRY_CAST(closed_date AS TIMESTAMP)) / 60.0
                                                    AS resolution_hours
FROM ranked
WHERE rn = 1;
