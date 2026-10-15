SELECT
    refund_id,
    payment_id,
    order_id,
    refund_amount,
    refund_timestamp,
    refund_status
FROM {{ source('silver', 'refunds') }}