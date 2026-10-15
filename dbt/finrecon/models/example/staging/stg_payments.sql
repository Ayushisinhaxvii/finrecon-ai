SELECT
    payment_id,
    order_id,
    amount,
    currency,
    payment_status,
    payment_timestamp
FROM {{ source('silver', 'payments') }}