SELECT
    payment_id,
    order_id,
    SUM(refund_amount) AS total_refund_amount,
    COUNT(*) AS refund_count,
    MIN(refund_timestamp) AS first_refund_timestamp,
    MAX(refund_timestamp) AS last_refund_timestamp
FROM {{ ref('stg_refunds') }}
GROUP BY
    payment_id,
    order_id