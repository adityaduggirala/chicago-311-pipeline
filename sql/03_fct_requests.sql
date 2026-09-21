CREATE OR REPLACE TABLE fct_requests AS
SELECT
    s.sr_number,
    d.request_type_key,
    s.status,
    s.origin,
    s.created_at,
    s.closed_at,
    CAST(s.created_at AS DATE) AS created_date,
    s.ward,
    s.community_area,
    s.resolution_hours,
    s.status = 'Open' AS is_open
FROM stg_requests s
LEFT JOIN dim_request_type d USING (sr_type);
